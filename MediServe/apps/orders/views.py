from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.db import transaction
from django.db.models import F, Max, Q
from apps.orders.models import Order, OrderItem
from apps.medicine.models import Medicine


# 🟢 Add medicine to order
@login_required
def add_to_order(request, medicine_id):
    medicine = get_object_or_404(Medicine, id=medicine_id)

    if request.method == "POST":
        quantity = int(request.POST.get("quantity", 1))
        special_request = request.POST.get("special_request", "")

        if quantity > medicine.total_stock:
            messages.warning(request, f"⚠️ Only {medicine.total_stock} available in stock.")
            return redirect("medicine_info", medicine_id=medicine.id)

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
        return redirect("order_list")

    return redirect("medicine_info", medicine_id=medicine.id)



# 🟢 Order List
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



# 🟢 Checkout
@login_required
def order_checkout(request):
    try:
        order = Order.objects.get(user=request.user, status="Pending")

        # Check stock
        can_checkout = True
        for item in order.items.all():
            if item.quantity > item.medicine.total_stock:
                can_checkout = False
                messages.warning(
                    request,
                    f"⚠️ Not enough stock for {item.medicine.name}. "
                    f"Available: {item.medicine.total_stock}, In cart: {item.quantity}"
                )

        if not can_checkout:
            return redirect("order_list")

        # Queue numbers
        if request.user.senior_citizen_id or request.user.pwd_id:
            last_priority = Order.objects.filter(
                Q(user__senior_citizen_id__isnull=False) |
                Q(user__pwd_id__isnull=False)
            ).aggregate(Max('queue_number'))['queue_number__max'] or 0
            order.queue_number = last_priority + 1
        else:
            max_queue = Order.objects.aggregate(Max('queue_number'))['queue_number__max'] or 0
            order.queue_number = max_queue + 1

        order.status = "Processing"
        order.save()

        messages.success(request, "✅ Your order has been placed!")
        return redirect("queue_status")

    except Order.DoesNotExist:
        messages.warning(request, "⚠️ No items in your cart.")
        return redirect("order_list")




# 🟢 Queue Status
@login_required
def queue_status(request):
    current_order = Order.objects.filter(user=request.user, status__in=['Pending', 'Processing']).first()
    serving_order = Order.objects.filter(status__in=['Pending', 'Processing']).order_by('queue_number').first()
    currently_serving = serving_order.queue_number if serving_order else 0

    estimated_wait = "3-5 days"

    context = {
        'current_order': current_order,
        'currently_serving': currently_serving,
        'estimated_wait': estimated_wait,
    }
    return render(request, "queue_page.html", context)



# 🟢 Track Delivery
@login_required
def track_delivery(request):
    orders = Order.objects.filter(user=request.user).exclude(status="Pending").order_by("-created_at")
    return render(request, "track_delivery.html", {"orders": orders})



# 🟢 Order History
@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user, status='Completed').order_by('-created_at')
    return render(request, 'order_history.html', {'orders': orders})



# 🟥 ADMIN: Delivery Control Page (FULLY UPDATED)
@login_required
@user_passes_test(lambda u: u.is_staff)
def delivery_page(request):

    if request.method == "POST":
        order_id = request.POST.get("order_id")
        action = request.POST.get("action")

        try:
            order = Order.objects.get(id=order_id)

            # ----------------------------------------------
            # 1️⃣ ASSIGN DRIVER (PERSISTENCE FIX)
            # ----------------------------------------------
            if action == "assign_driver":
                driver_label = request.POST.get("driver_name")

                if driver_label:
                    order.driver = driver_label  # store LABEL not key
                    order.save()
                    messages.success(request, f"🚗 Driver assigned to Order #{order_id}")
                else:
                    messages.warning(request, "⚠️ No driver selected.")

                return redirect("delivery_page")

            # ----------------------------------------------
            # 2️⃣ PROCESS ORDER
            # ----------------------------------------------
            elif action == "process" and order.status == "Pending":
                order.status = "Processing"
                order.save()
                messages.success(request, f"⚙️ Order #{order_id} is now being processed.")
                return redirect("delivery_page")

            # ----------------------------------------------
            # 3️⃣ SHIP ORDER — DRIVER REQUIRED
            # ----------------------------------------------
            elif action == "ship" and order.status == "Processing":

                if not order.driver:
                    messages.error(
                        request,
                        f"⚠️ Cannot ship Order #{order_id}. Please assign a driver first."
                    )
                    return redirect("delivery_page")

                order.status = "Shipped"
                order.save()
                messages.success(request, f"🚚 Order #{order_id} is now out for delivery!")
                return redirect("delivery_page")

            # ----------------------------------------------
            # 4️⃣ COMPLETE ORDER
            # ----------------------------------------------
            elif action == "complete" and order.status == "Shipped":
                order.status = "Completed"
                order.completed_at = timezone.now()
                order.save()
                messages.success(request, f"🏁 Order #{order_id} marked completed!")
                return redirect("delivery_page")

            # ----------------------------------------------
            # 5️⃣ CANCEL ORDER
            # ----------------------------------------------
            elif action == "cancel" and order.status in ["Pending", "Processing"]:
                order.status = "Cancelled"
                order.save()
                messages.success(request, f"❌ Order #{order_id} cancelled.")
                return redirect("delivery_page")

            # ----------------------------------------------
            # 6️⃣ REOPEN ORDER
            # ----------------------------------------------
            elif action == "reopen" and order.status in ["Completed", "Cancelled"]:
                order.status = "Pending"
                order.save()
                messages.success(request, f"🔄 Order #{order_id} reopened.")
                return redirect("delivery_page")

            else:
                messages.warning(request, "⚠️ Action not allowed.")
                return redirect("delivery_page")

        except Order.DoesNotExist:
            messages.error(request, "❌ Order not found.")
            return redirect("delivery_page")

    # LOAD ORDERS & DRIVERS
    orders = Order.objects.exclude(status="Completed").order_by("-created_at")
    drivers = Order.DRIVER_CHOICES

    return render(request, "delivery_page.html", {"orders": orders, "drivers": drivers})



# 🟢 Remove Order Item
@login_required
def remove_order_item(request, item_id):
    item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)
    medicine_name = item.medicine.name
    item.delete()

    if item.order.items.count() == 0:
        item.order.delete()

    messages.success(request, f"🗑️ {medicine_name} removed from your order.")
    return redirect("order_list")



# 🟢 Update Order Item Quantity
@login_required
def update_order_item(request, item_id):
    if request.method == "POST":
        item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)
        quantity = int(request.POST.get("quantity", 1))

        if quantity <= 0:
            item.delete()
            messages.success(request, f"🗑️ {item.medicine.name} removed.")
        elif quantity > item.medicine.total_stock:
            messages.warning(request, f"⚠️ Only {item.medicine.total_stock} available.")
        else:
            item.quantity = quantity
            item.save()
            messages.success(request, f"📝 Updated quantity.")

    return redirect("order_list")



# 🟢 Admin: Manual complete action
@login_required
@user_passes_test(lambda u: u.is_staff)
def mark_order_completed(request, order_id):
    if request.method == "POST":
        try:
            order = Order.objects.get(id=order_id)
            if order.status == "Shipped":
                order.status = "Completed"
                order.save()
                messages.success(request, "Order marked completed!")
            else:
                messages.warning(request, "Order must be shipped first.")
        except Order.DoesNotExist:
            messages.error(request, "Order not found.")
    return redirect("delivery_page")



# 🟢 Order Detail
@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, "order_detail.html", {"order": order})
