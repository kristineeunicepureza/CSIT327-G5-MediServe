from django.urls import path
from . import views

urlpatterns = [
    # Main dashboard page
    path("", views.analytics_dashboard, name="analytics"),

    # API endpoints
    path("api/kpis/", views.analytics_kpi_data, name="analytics_kpis"),
    path("api/orders-per-month/", views.orders_per_month_data, name="analytics_orders_per_month"),
    path("api/top-medicines/", views.top_medicines_data, name="analytics_top_medicines"),
    path("api/order-status-breakdown/", views.order_status_breakdown_data, name="analytics_order_status_breakdown"),
    path("api/stock-breakdown/", views.stock_breakdown_data, name="analytics_stock_breakdown"),
    path("api/announcements-per-month/", views.announcements_per_month_data, name="analytics_announcements_per_month"),
]
