from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.db import transaction, models
from django.http import JsonResponse
from django.db.models import F, Max, Q
from apps.orders.models import Order, OrderItem
from apps.medicine.models import Medicine


# 🟢 Add medicine to order - UPDATED with prescription and limit validation
@login_required
def add_to_order(request, medicine_id):
    medicine = get_object_or_404(Medicine, id=medicine_id)

    # ✅ NEW: Check if medicine can be ordered (non-prescription only)
    if not medicine.can_be_ordered():
        if medicine.prescription_type == 'prescription':
            messages.error(
                request,
                f"❌ {medicine.name} requires a prescription and cannot be ordered online. "
                f"Please consult with healthcare staff at the health center."
            )
        elif medicine.status != 'active':
            messages.error(request, f"❌ {medicine.name} is not currently available for ordering.")
        else:
            messages.error(request, f"❌ {medicine.name} cannot be ordered online.")
        return redirect("medicine_catalog")

    if request.method == "POST":
        quantity = int(request.POST.get("quantity", 1))
        special_request = request.POST.get("special_request", "")

        # ✅ NEW: Validate order quantity limits
        max_quantity = medicine.get_max_order_quantity()
        if quantity > max_quantity:
            limit_text = "3 days" if medicine.order_limit == '3_days' else "1 week"
            messages.warning(
                request,
                f"⚠️ Order limit exceeded! {medicine.name} can only be ordered for {limit_text} supply "
                f"(maximum {max_quantity} units per order)."
            )
            return redirect("medicine_info", medicine_id=medicine.id)

        # Existing stock validation
        if quantity > medicine.total_stock:
            messages.warning(request, f"⚠️ Only {medicine.total_stock} available in stock.")
            return redirect("medicine_info", medicine_id=medicine.id)

        # Check for existing pending order with same medicine
        order, created = Order.objects.get_or_create(
            user=request.user,
            status="Pending",
            defaults={"created_at": timezone.now()}
        )

        # Check if item already exists
        try:
            item = OrderItem.objects.get(order=order, medicine=medicine)
            # ✅ NEW: Validate total quantity (existing + new) doesn't exceed limits
            total_quantity = item.quantity + quantity
            if total_quantity > max_quantity:
                limit_text = "3 days" if medicine.order_limit == '3_days' else "1 week"
                messages.warning(
                    request,
                    f"⚠️ Total order limit exceeded! You already have {item.quantity} units of {medicine.name} "
                    f"in your cart. Maximum allowed is {max_quantity} units ({limit_text} supply)."
                )
                return redirect("medicine_info", medicine_id=medicine.id)

            # Item exists, increment quantity
            item.quantity += quantity
            if special_request:
                item.special_request = special_request
            item.save()
            item_created = False
        except OrderItem.DoesNotExist:
            # Item doesn't exist, create it
            item = OrderItem.objects.create(
                order=order,
                medicine=medicine,
                quantity=quantity,
                special_request=special_request
            )
            item_created = True

        limit_text = "3 days" if medicine.order_limit == '3_days' else "1 week"
        messages.success(
            request,
            f"✅ Added {quantity} × {medicine.name} to your order ({limit_text} supply limit)."
        )
        return redirect("order_list")

    return redirect("medicine_info", medicine_id=medicine.id)


@login_required
def order_list(request):
    orders = Order.objects.filter(user=request.user, status="Pending")
    items = OrderItem.objects.filter(order__in=orders) if orders.exists() else OrderItem.objects.none()
    total_quantity = sum(item.quantity for item in items)

    context = {
        "items": items,
        "total_quantity": total_quantity,
        "has_items": items.exists()
    }
    return render(request, "order_list.html", context)


# 🟢 Checkout - place order
@login_required
def order_checkout(request):
    try:
        order = Order.objects.get(user=request.user, status="Pending")

        # Check stock availability and order limits
        can_checkout = True
        for item in order.items.all():
            # Check stock
            if item.quantity > item.medicine.total_stock:
                can_checkout = False
                messages.warning(
                    request,
                    f"⚠️ Not enough stock for {item.medicine.name}. "
                    f"Available: {item.medicine.total_stock}, In cart: {item.quantity}"
                )

            # ✅ NEW: Check order limits
            max_quantity = item.medicine.get_max_order_quantity()
            if item.quantity > max_quantity:
                can_checkout = False
                limit_text = "3 days" if item.medicine.order_limit == '3_days' else "1 week"
                messages.warning(
                    request,
                    f"⚠️ Order limit exceeded for {item.medicine.name}. "
                    f"Maximum allowed: {max_quantity} units ({limit_text} supply)"
                )

            # ✅ NEW: Check if medicine is still orderable
            if not item.medicine.can_be_ordered():
                can_checkout = False
                messages.error(
                    request,
                    f"❌ {item.medicine.name} is no longer available for ordering (prescription required)."
                )

        if not can_checkout:
            return redirect("order_list")

        # IMPORTANT: Assign queue number FIRST while status is still "Pending"
        order.assign_queue_number()

        # THEN change status to Processing
        order.status = "Processing"
        order.save()

        # Show priority message if applicable
        if order.is_priority_user():
            messages.success(
                request,
                f"✅ Your order has been placed with PRIORITY (Senior Citizen/Person with Disability)! "
                f"You are Queue #{order.queue_number}. Check your queue status below."
            )
        else:
            messages.success(
                request,
                f"✅ Your order has been placed! You are Queue #{order.queue_number}. "
                f"Check your queue status below."
            )

        return redirect("queue_status")

    except Order.DoesNotExist:
        messages.warning(request, "⚠️ No items in your cart.")
        return redirect("order_list")


@login_required
def queue_status(request):
    current_order = Order.objects.filter(
        user=request.user,
        status__in=['Pending', 'Processing']
    ).first()

    serving_order = Order.objects.filter(
        status__in=['Pending', 'Processing']
    ).order_by('queue_number').first()

    currently_serving = serving_order.queue_number if serving_order else 0

    position = None
    estimated_wait = "1-2 hours"
    is_almost_turn = False
    total_ahead = 0
    is_priority = False

    if current_order:
        position = current_order.get_queue_position()
        is_priority = current_order.is_priority_user()

        if position:
            total_ahead = position - 1
            if position == 1:
                estimated_wait = "20-30 minutes"
            elif position <= 5:
                estimated_wait = "30-40 minutes"
            else:
                estimated_wait = "50-60 minutes"
            is_almost_turn = position <= 3

    context = {
        'current_order': current_order,
        'currently_serving': currently_serving,
        'estimated_wait': estimated_wait,
        'position': position,
        'is_almost_turn': is_almost_turn,
        'total_ahead': total_ahead,
        'is_priority': is_priority,
    }
    return render(request, "queue_page.html", context)


# Updated API (returns additional fields including priority status)
@login_required
def queue_status_api(request):
    current_order = Order.objects.filter(
        user=request.user,
        status__in=['Pending', 'Processing']
    ).first()

    serving_order = Order.objects.filter(
        status__in=['Pending', 'Processing']
    ).order_by('queue_number').first()

    currently_serving = serving_order.queue_number if serving_order else 0

    position = None
    estimated_wait = "1-2 hours"
    is_almost_turn = False
    total_ahead = 0
    is_priority = False

    if current_order:
        position = current_order.get_queue_position()
        is_priority = current_order.is_priority_user()

        if position:
            total_ahead = position - 1
            if position == 1:
                estimated_wait = "20-30 minutes"
            elif position <= 5:
                estimated_wait = "30-40 minutes"
            else:
                estimated_wait = "50-60 minutes"
            is_almost_turn = position <= 3

    data = {
        'queue_number': current_order.queue_number if current_order else None,
        'currently_serving': currently_serving,
        'estimated_wait': estimated_wait,
        'status': current_order.status if current_order else None,
        'position': position,
        'is_almost_turn': is_almost_turn,
        'total_ahead': total_ahead,
        'is_priority': is_priority,
        'items': [
            {'name': item.medicine.name, 'quantity': item.quantity}
            for item in current_order.items.all()
        ] if current_order else []
    }
    return JsonResponse(data)


@login_required
def track_delivery(request):
    # Show all orders except Pending (includes Shipped, Completed, Cancelled)
    orders = Order.objects.filter(
        user=request.user
    ).exclude(status="Pending").order_by("-created_at")

    return render(request, "track_delivery.html", {"orders": orders})


@login_required
def order_history(request):
    orders = Order.objects.filter(
        user=request.user,
        status='Completed'
    ).order_by('-completed_at', '-created_at')

    return render(request, 'order_history.html', {'orders': orders})


@login_required
@user_passes_test(lambda u: u.is_staff)
def delivery_page(request):
    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        action = request.POST.get('action')

        try:
            order = Order.objects.get(id=order_id)

            # Validation: Ensure sequential processing for queue orders
            if action in ['process', 'ship']:
                next_in_queue = Order.objects.filter(
                    status__in=['Pending', 'Processing']
                ).order_by('queue_number').first()

                if next_in_queue and order != next_in_queue:
                    priority_msg = " (PRIORITY)" if next_in_queue.is_priority_user() else ""
                    messages.warning(
                        request,
                        f"⚠️ You must process Order #{next_in_queue.id} first "
                        f"(Queue #{next_in_queue.queue_number}{priority_msg})."
                    )
                    return redirect('delivery_page')

            if action == 'assign_driver':
                driver_name = request.POST.get('driver_name')
                if driver_name:
                    order.driver = driver_name
                    order.save()
                    messages.success(request, f"✅ Driver {driver_name} assigned to Order #{order_id}.")
                else:
                    messages.warning(request, "⚠️ No driver selected.")

            elif action == 'process' and order.status == 'Pending':
                order.status = 'Processing'
                order.save()
                messages.success(request, f"✅ Order #{order_id} is now being processed.")

            elif action == 'ship' and order.status == 'Processing':
                # Validate: Driver must be assigned before shipping
                if not order.driver:
                    messages.error(
                        request,
                        f"❌ Cannot ship Order #{order_id} without a driver assigned. "
                        f"Please assign a driver first."
                    )
                    return redirect('delivery_page')

                order.status = 'Shipped'
                order.save()
                # Remove from queue when shipped (but order remains visible)
                order.remove_from_queue()
                messages.success(request, f"🚚 Order #{order_id} is out for delivery!")

            elif action == 'complete' and order.status == 'Shipped':
                order.status = 'Completed'
                order.completed_at = timezone.now()
                order.save()
                messages.success(request, f"🏁 Order #{order_id} marked as completed!")

            elif action == 'archive' and order.status == 'Completed':
                order.is_archived = True
                order.save()
                messages.success(request, f"📦 Order #{order_id} has been archived.")

            elif action == 'cancel' and order.status in ['Pending', 'Processing']:
                order.status = 'Cancelled'
                order.save()
                # Remove from queue when cancelled
                order.remove_from_queue()
                messages.success(request, f"❌ Order #{order_id} has been cancelled.")

            elif action == 'reopen' and order.status in ['Completed', 'Cancelled']:
                order.status = 'Processing'
                # Re-assign queue number on reopen (respects priority)
                order.assign_queue_number()
                messages.success(request, f"🔄 Order #{order_id} reopened and added back to queue.")

            else:
                messages.warning(request, f"⚠️ Action '{action}' cannot be applied to Order #{order_id}.")

        except Order.DoesNotExist:
            messages.error(request, f"❌ Order #{order_id} not found.")

        return redirect('delivery_page')

    # Get all orders except archived ones
    # Split into orders with queue numbers and without, then combine
    orders_with_queue = Order.objects.filter(
        is_archived=False,
        queue_number__isnull=False
    ).select_related('user').order_by('queue_number')

    orders_without_queue = Order.objects.filter(
        is_archived=False,
        queue_number__isnull=True
    ).select_related('user').order_by('-created_at')

    # Combine: queued orders first, then non-queued
    orders = list(orders_with_queue) + list(orders_without_queue)

    # Get archived orders
    archived_orders = Order.objects.filter(
        is_archived=True
    ).select_related('user').order_by('-completed_at')

    drivers = Order.DRIVER_CHOICES

    context = {
        'orders': orders,
        'archived_orders': archived_orders,
        'drivers': drivers,
    }

    return render(request, 'delivery_page.html', context)


@login_required
def remove_order_item(request, item_id):
    item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)
    medicine_name = item.medicine.name
    item.delete()

    # If no items left, delete the order
    if item.order.items.count() == 0:
        item.order.delete()

    messages.success(request, f"🗑️ {medicine_name} removed from your order.")
    return redirect("order_list")


@login_required
def update_order_item(request, item_id):
    if request.method == "POST":
        item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)
        quantity = int(request.POST.get("quantity", 1))

        if quantity <= 0:
            item.delete()
            messages.success(request, f"🗑️ {item.medicine.name} removed from your order.")
        elif quantity > item.medicine.total_stock:
            messages.warning(request, f"⚠️ Only {item.medicine.total_stock} available in stock.")
        else:
            # ✅ NEW: Check order limits when updating quantity
            max_quantity = item.medicine.get_max_order_quantity()
            if quantity > max_quantity:
                limit_text = "3 days" if item.medicine.order_limit == '3_days' else "1 week"
                messages.warning(
                    request,
                    f"⚠️ Order limit exceeded! {item.medicine.name} can only be ordered for {limit_text} supply "
                    f"(maximum {max_quantity} units per order)."
                )
            else:
                item.quantity = quantity
                item.save()
                messages.success(request, f"📝 {item.medicine.name} quantity updated to {quantity}.")

    return redirect("order_list")


@login_required
@user_passes_test(lambda u: u.is_staff)
def mark_order_completed(request, order_id):
    if request.method == 'POST':
        try:
            order = Order.objects.get(id=order_id)
            if order.status == 'Shipped':
                order.status = 'Completed'
                order.completed_at = timezone.now()
                order.save()
                messages.success(request, f"✅ Order #{order_id} marked as completed!")
            else:
                messages.warning(request, f"⚠️ Order #{order_id} must be shipped before marking as completed.")
        except Order.DoesNotExist:
            messages.error(request, "Order not found.")

    return redirect('delivery_page')


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, "order_detail.html", {"order": order})