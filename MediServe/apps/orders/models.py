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

    # NEW: driver name stored directly
    driver = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        choices=DRIVER_CHOICES
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")

    class Meta:
        db_table = "tblorders"
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.id} - {self.user.first_name} {self.user.last_name} ({self.status})"

    def get_total_quantity(self):
        return sum(item.quantity for item in self.items.all())


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    special_request = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "tblorderitems"

    def __str__(self):
        return f"{self.medicine.name} × {self.quantity}"
