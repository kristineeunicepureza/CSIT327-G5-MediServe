from django.db import models
from django.conf import settings
from apps.medicine.models import Medicine


class Order(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Processing", "Processing"),
        ("Shipped", "Out for Delivery"),
        ("Completed", "Completed"),
        ("Cancelled", "Cancelled"),
    ]

    DRIVERS = [
        "Marco Dela Cruz",
        "Johnrey Santos",
        "Carlito Mendoza",
        "Jerome Villanueva",
        "Renzo Ramirez",
        "Gabriel Torres",
        "Alfred Navarro",
        "Kristoffer Soriano",
        "Ralph Gutierrez",
        "Leo Manalang",
    ]
    DRIVER_CHOICES = [(driver, driver) for driver in DRIVERS]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    driver = models.CharField(max_length=255, null=True, blank=True, choices=DRIVER_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    queue_number = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        db_table = "tblorders"
        ordering = ['queue_number', '-created_at']

    def __str__(self):
        return f"Order #{self.id} - {self.user.full_name} ({self.status})"

    def assign_queue_number(self):
        # Get all pending orders
        pending_orders = Order.objects.filter(status='Pending').order_by('queue_number')

        # Priority users: Senior Citizen or PWD
        if self.user.senior_citizen_id or self.user.pwd_id:
            priority_orders = pending_orders.filter(user__senior_citizen_id__isnull=True, user__pwd_id__isnull=True)
            if priority_orders.exists():
                self.queue_number = priority_orders.first().queue_number
                # Increment queue_number for others
                for order in priority_orders:
                    order.queue_number += 1
                    order.save()
            else:
                self.queue_number = pending_orders.count() + 1
        else:
            self.queue_number = pending_orders.count() + 1
        self.save()

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    special_request = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "tblorderitems"

    def __str__(self):
        return f"{self.medicine.name} × {self.quantity}"