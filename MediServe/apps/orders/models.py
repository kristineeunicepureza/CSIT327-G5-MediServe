from django.db import models
from django.conf import settings
from apps.medicine.models import Medicine


class Order(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending"),  # user just placed the order
        ("Processing", "Processing"),  # admin confirmed
        ("Shipped", "Out for Delivery"),  # admin shipped it
        ("Completed", "Completed"),  # delivery done
        ("Cancelled", "Cancelled"),  # cancelled manually
    ]


    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
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
        """Calculate total quantity of all items in the order"""
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