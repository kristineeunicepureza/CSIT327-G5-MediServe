from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from apps.medicine.models import Medicine, MedicineBatch
from .models import Order, OrderItem

User = get_user_model()


# 🟢 Add medicine to order
@login_required
def add_to_order(request, medicine_id):
    medicine = get_object_or_404(Medicine, id=medicine_id)

    if request.method == "POST":
        quantity = int(request.POST.get("quantity", 1))
        special_request = request.POST.get("special_request", "")

        # ✅ USE total_stock PROPERTY INSTEAD OF stock_quantity
        if quantity > medicine.total_stock:
            messages.warning(request, f"⚠️ Only {medicine.total_stock} available in stock.")
            return redirect("medicine_info", medicine_id=medicine.id)

        # Get or create pending order (cart)
        order, created = Order.objects.get_or_create(
            user=request.user,
            status="Pending",
            defaults={"created_at": timezone.now()}
        )

        item, item_created = OrderItem.objects.get_or_create(
            order=order,
            medicine=medicine,
            defaults={"quantity": quantity, "special_request": special_request}
        )

        if not item_created:
            item.quantity += quantity
            if special_request:
                item.special_request = special_request
            item.save()

        messages.success(request, f"✅ Added {quantity} × {medicine.name} to your order.")

        # 🔧 Redirect to order_list (Current Orders) to review cart
        return redirect("order_list")

    # GET request - just show the medicine info page
    return redirect("medicine_info", medicine_id=medicine.id)


@login_required
def order_list(request):
    """Display current orders (cart) for the user."""
    # Get pending orders for the user
    orders = Order.objects.filter(user=request.user, status="Pending")

    # Get all items from pending orders
    items = OrderItem.objects.filter(order__in=orders) if orders.exists() else OrderItem.objects.none()

    # Calculate total quantity for modal display
    total_quantity = sum(item.quantity for item in items)

    context = {
        "items": items,
        "total_quantity": total_quantity,
        "has_items": items.exists()
    }

    return render(request, "order_list.html", context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def delivery_page(request):
    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        action = request.POST.get('action')

        try:
            order = Order.objects.get(id=order_id)

            # ASSIGN DRIVER
            if action == 'assign_driver':
                driver_name = request.POST.get('driver_name')

                # If the dropdown has value, assign driver
                if driver_name and driver_name != "":
                    order.driver = driver_name
                    order.save()
                    messages.success(request, f"✅ Driver {driver_name} assigned to Order #{order_id}.")

                # If the dropdown is empty, DO NOT automatically remove driver
                elif driver_name == "":
                    messages.warning(request, f"⚠️ No driver selected. Please choose a driver.")

            # PROCESS
            elif action == 'process':
                if order.status == 'Pending':
                    order.status = 'Processing'
                    order.save()
                    messages.success(request, f"✅ Order #{order_id} is now being processed.")
                else:
                    messages.warning(request, f"⚠️ Order #{order_id} cannot be processed from {order.status}.")

            # SHIP
            elif action == 'ship':
                if order.status == 'Processing':
                    order.status = 'Shipped'
                    order.save()
                    messages.success(request, f"🚚 Order #{order_id} is out for delivery!")
                else:
                    messages.warning(request, f"⚠️ Order #{order_id} must be Processing to ship.")

            # COMPLETE
            elif action == 'complete':
                if order.status == 'Shipped':
                    order.status = 'Completed'
                    order.completed_at = timezone.now()
                    order.save()
                    messages.success(request, f"🏁 Order #{order_id} marked as completed!")
                else:
                    messages.warning(request, f"⚠️ Order #{order_id} must be Shipped to complete.")

            # CANCEL
            elif action == 'cancel':
                if order.status in ['Pending', 'Processing']:
                    order.status = 'Cancelled'
                    order.save()
                    messages.success(request, f"❌ Order #{order_id} has been cancelled.")
                else:
                    messages.warning(request, f"⚠️ Order #{order_id} cannot be cancelled from {order.status}.")

            # REOPEN
            elif action == 'reopen':
                if order.status in ['Completed', 'Cancelled']:
                    order.status = 'Pending'
                    order.save()
                    messages.success(request, f"🔄 Order #{order_id} reopened.")

        except Order.DoesNotExist:
            messages.error(request, f"❌ Order #{order_id} not found.")

        return redirect('delivery_page')

    # GET request
    orders = Order.objects.exclude(status='Completed').order_by('-created_at')
    drivers = Order.DRIVER_CHOICES  # NEW — pulled directly from model

    context = {
        'orders': orders,
        'drivers': drivers,
    }
    return render(request, 'delivery_page.html', context)


@login_required
def remove_order_item(request, item_id):
    item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)
    medicine_name = item.medicine.name
    item.delete()

    if item.order.items.count() == 0:
        item.order.delete()

    messages.success(request, f"🗑️ {medicine_name} removed from your order.")
    return redirect("order_list")


@login_required
def update_order_item(request, item_id):
    if request.method == "POST":
        item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)
        quantity = int(request.POST.get("quantity", 1))

        total_available = item.medicine.total_stock

        if quantity <= 0:
            item.delete()
            messages.success(request, f"🗑️ {item.medicine.name} removed from your order.")
        elif quantity > total_available:
            messages.warning(request, f"⚠️ Only {total_available} available in stock.")
        else:
            item.quantity = quantity
            item.save()
            messages.success(request, f"📝 {item.medicine.name} quantity updated to {quantity}.")

    return redirect("order_list")


# 🟢 Checkout
@login_required
def order_checkout(request):
    try:
        # Get the user's pending order (cart)
        order = Order.objects.get(user=request.user, status="Pending")

        # Check stock availability using total_stock property
        can_checkout = True
        for item in order.items.all():
            if item.quantity > item.medicine.total_stock:  # ✅ USE total_stock
                can_checkout = False
                messages.warning(
                    request,
                    f"⚠️ Not enough stock for {item.medicine.name}. "
                    f"Available: {item.medicine.total_stock}, In cart: {item.quantity}"
                )

        if not can_checkout:
            return redirect("order_list")

        # Change status from Pending (cart) to Processing (checked out)
        order.status = "Processing"
        order.save()
        messages.success(request, "✅ Your order has been submitted successfully! Track your delivery below.")

        # 🔧 Redirect to track_delivery after submitting order
        return redirect("track_delivery")

    except Order.DoesNotExist:
        messages.warning(request, "⚠️ No items in your cart.")
        return redirect("order_list")


@login_required
def track_delivery(request):
    orders = Order.objects.filter(user=request.user).exclude(status="Pending").order_by("-created_at")
    return render(request, "track_delivery.html", {"orders": orders})


@login_required
def order_history(request):
    """Display order history - only completed orders."""
    # Only show orders with status "Completed"
    orders = Order.objects.filter(
        user=request.user,
        status='Completed'
    ).order_by('-created_at')

    context = {
        'orders': orders,
    }
    return render(request, 'order_history.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def mark_order_completed(request, order_id):
    """Mark an order as completed after delivery."""
    if request.method == 'POST':
        try:
            order = Order.objects.get(id=order_id)

            # Only allow completion if order is shipped
            if order.status == 'Shipped':
                order.status = 'Completed'
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