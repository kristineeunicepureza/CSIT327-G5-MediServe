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
        """
        Assign queue number with priority for Senior Citizens and PWD.
        Priority users ALWAYS go to the front of the queue, even pushing regular users back.
        """
        # Get all active orders in queue (Pending or Processing), excluding self
        pending_orders = Order.objects.filter(
            status__in=['Pending', 'Processing'],
            queue_number__isnull=False  # Only orders with queue numbers
        ).exclude(pk=self.pk).order_by('queue_number')

        # Check if current user is priority (Senior Citizen or PWD)
        is_priority = self.user.senior_citizen_id or self.user.pwd_id

        if is_priority:
            # Priority users: ALWAYS insert at position 1 (top of queue)
            # Find ALL regular (non-priority) users in queue
            regular_orders = pending_orders.filter(
                user__senior_citizen_id__isnull=True,
                user__pwd_id__isnull=True
            ).order_by('queue_number')

            # Find ALL priority users in queue
            priority_orders = pending_orders.filter(
                models.Q(user__senior_citizen_id__isnull=False) |
                models.Q(user__pwd_id__isnull=False)
            ).order_by('queue_number')

            if regular_orders.exists():
                # There are regular users in the queue
                # Insert this priority user right after the last priority user
                # OR at position 1 if no priority users exist

                if priority_orders.exists():
                    # Put after the last priority user
                    last_priority = priority_orders.last()
                    insert_position = last_priority.queue_number + 1
                    self.queue_number = insert_position

                    # Shift all orders AT or AFTER this position by +1
                    orders_to_shift = pending_orders.filter(
                        queue_number__gte=insert_position
                    ).order_by('queue_number')

                    for order in orders_to_shift:
                        order.queue_number += 1
                        order.save()
                else:
                    # No priority users, insert at position 1 (front of queue)
                    self.queue_number = 1

                    # Shift ALL orders by +1
                    for order in pending_orders.order_by('queue_number'):
                        order.queue_number += 1
                        order.save()
            else:
                # Only priority users in queue (or no orders at all)
                if priority_orders.exists():
                    last_priority = priority_orders.last()
                    self.queue_number = last_priority.queue_number + 1
                else:
                    # No orders at all, start at 1
                    self.queue_number = 1
        else:
            # Regular users: Always append to the end
            if pending_orders.exists():
                last_order = pending_orders.order_by('-queue_number').first()
                self.queue_number = last_order.queue_number + 1
            else:
                # No orders at all
                self.queue_number = 1

        self.save()

    def remove_from_queue(self):
        """
        Remove this order from queue and shift others down by 1.
        This is called when order is Shipped or Cancelled.
        """
        if self.queue_number:
            current_queue = self.queue_number

            # Get all orders with queue_number greater than this one
            orders_to_shift = Order.objects.filter(
                status__in=['Pending', 'Processing'],
                queue_number__gt=current_queue
            ).order_by('queue_number')

            # Shift queue numbers down by 1
            for order in orders_to_shift:
                order.queue_number -= 1
                order.save()

            # Clear this order's queue number
            self.queue_number = None
            self.save()

    def get_queue_position(self):
        """
        Returns the user's position in the active queue (Pending or Processing).
        Priority users (Senior Citizen/PWD) are always at the front.
        Returns None if not in queue.
        """
        if self.status not in ['Pending', 'Processing']:
            return None

        # Get all active orders ordered by queue_number
        active_orders = Order.objects.filter(
            status__in=['Pending', 'Processing']
        ).order_by('queue_number', 'created_at')

        for position, order in enumerate(active_orders, start=1):
            if order.pk == self.pk:
                return position

        return None

    def can_user_access(self, user):
        """
        Validation: Only the order's owner can access queue details.
        """
        return self.user == user

    def is_priority_user(self):
        """
        Helper method to check if the order belongs to a priority user.
        """
        return bool(self.user.senior_citizen_id or self.user.pwd_id)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    special_request = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "tblorderitems"

    def __str__(self):
        return f"{self.medicine.name} × {self.quantity}"