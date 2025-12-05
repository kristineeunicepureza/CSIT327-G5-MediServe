from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth

from apps.accounts.models import Account
from apps.medicine.models import Medicine
from apps.orders.models import Order, OrderItem
from apps.announcements.models import Announcement


def _is_admin(user):
    """
    Reuse the same admin logic you used in announcements:
    - staff users
    - or the hard-coded admin email
    """
    if not user.is_authenticated:
        return False
    return user.is_staff or (user.email and user.email.lower() == "admin123@gmail.com")


# 🔹 Main Analytics Dashboard Page (HTML)
@login_required
def analytics_dashboard(request):
    if not _is_admin(request.user):
        messages.error(request, "Access denied. Admins only.")
        return redirect("main_menu")

    return render(request, "analytics.html")


# 🔹 KPIs / Summary Metrics
@login_required
def analytics_kpi_data(request):
    if not _is_admin(request.user):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    now = timezone.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_users = Account.objects.count()
    total_admins = Account.objects.filter(is_staff=True).count()
    active_users = Account.objects.filter(is_active=True).count()
    new_users_this_month = Account.objects.filter(created_at__gte=start_of_month).count()

    total_medicines = Medicine.objects.count()

    # Stock breakdown (simple threshold, can be adjusted)
    low_stock_threshold = 10
    low_stock = 0
    out_of_stock = 0
    normal_stock = 0

    for med in Medicine.objects.all():
        stock = med.total_stock  # property on Medicine model
        if stock == 0:
            out_of_stock += 1
        elif stock < low_stock_threshold:
            low_stock += 1
        else:
            normal_stock += 1

    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status="Pending").count()
    completed_orders = Order.objects.filter(status="Completed").count()
    cancelled_orders = Order.objects.filter(status="Cancelled").count()

    total_announcements = Announcement.objects.count()

    data = {
        "users": {
            "total": total_users,
            "admins": total_admins,
            "active": active_users,
            "new_this_month": new_users_this_month,
        },
        "medicine": {
            "total": total_medicines,
            "low_stock": low_stock,
            "out_of_stock": out_of_stock,
            "normal_stock": normal_stock,
        },
        "orders": {
            "total": total_orders,
            "pending": pending_orders,
            "completed": completed_orders,
            "cancelled": cancelled_orders,
        },
        "announcements": {
            "total": total_announcements,
        },
    }
    return JsonResponse(data)


# 🔹 Orders per month (for line chart)
@login_required
def orders_per_month_data(request):
    if not _is_admin(request.user):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    qs = (
        Order.objects
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )

    data = []
    for row in qs:
        month = row["month"]
        if month:
            label = month.strftime("%b %Y")  # e.g., 'Dec 2025'
        else:
            label = "Unknown"
        data.append({
            "label": label,
            "count": row["count"],
        })

    return JsonResponse({"data": data})


# 🔹 Top 5 medicines by ordered quantity (bar chart)
@login_required
def top_medicines_data(request):
    if not _is_admin(request.user):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    qs = (
        OrderItem.objects
        .values("medicine__name")
        .annotate(total_quantity=Sum("quantity"))
        .order_by("-total_quantity")[:5]
    )

    data = [
        {
            "name": row["medicine__name"],
            "total_quantity": row["total_quantity"],
        }
        for row in qs
    ]

    return JsonResponse({"data": data})


# 🔹 Order status breakdown (pie chart)
@login_required
def order_status_breakdown_data(request):
    if not _is_admin(request.user):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    qs = (
        Order.objects
        .values("status")
        .annotate(count=Count("id"))
        .order_by("status")
    )

    data = [
        {
            "status": row["status"],
            "count": row["count"],
        }
        for row in qs
    ]

    return JsonResponse({"data": data})


# 🔹 Medicine stock breakdown (donut chart)
@login_required
def stock_breakdown_data(request):
    if not _is_admin(request.user):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    low_stock_threshold = 10
    low_stock = 0
    out_of_stock = 0
    normal_stock = 0

    for med in Medicine.objects.all():
        stock = med.total_stock
        if stock == 0:
            out_of_stock += 1
        elif stock < low_stock_threshold:
            low_stock += 1
        else:
            normal_stock += 1

    data = {
        "labels": ["Out of Stock", "Low Stock", "Normal Stock"],
        "values": [out_of_stock, low_stock, normal_stock],
    }
    return JsonResponse({"data": data})


# 🔹 Announcements per month (optional extra chart)
@login_required
def announcements_per_month_data(request):
    if not _is_admin(request.user):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    qs = (
        Announcement.objects
        .annotate(month=TruncMonth("date_posted"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )

    data = []
    for row in qs:
        month = row["month"]
        label = month.strftime("%b %Y") if month else "Unknown"
        data.append({
            "label": label,
            "count": row["count"],
        })

    return JsonResponse({"data": data})
