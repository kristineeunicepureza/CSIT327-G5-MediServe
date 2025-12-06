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
    is_archived = models.BooleanField(default=False)

    class Meta:
        db_table = "tblorders"
        ordering = ['queue_number', '-created_at']

    def __str__(self):
        return f"Order #{self.id} - {self.user.full_name} ({self.status})"

    def assign_queue_number(self):
        """
        Assign queue number with PRIORITY override for Senior Citizens and PWD.
        When a priority user orders, ALL existing regular users get pushed down.

        Final queue order:
        - Queue #1, #2, #3... = All priority users (Senior/PWD) in order of placement
        - Queue #N+1, #N+2... = All regular users in order of placement
        """
        # Get ALL active orders (Pending or Processing), excluding self - including those without queue numbers yet
        all_pending = Order.objects.filter(
            status__in=['Pending', 'Processing']
        ).exclude(pk=self.pk).order_by('created_at')

        # Separate priority and regular users by their ORIGINAL order
        # Priority users have uploaded senior_citizen_id OR pwd_id files (not empty strings)
        priority_orders = all_pending.filter(
            models.Q(user__senior_citizen_id__isnull=False, user__senior_citizen_id__gt='') |
            models.Q(user__pwd_id__isnull=False, user__pwd_id__gt='')
        ).order_by('created_at')

        regular_orders = all_pending.filter(
            models.Q(user__senior_citizen_id__isnull=True) | models.Q(user__senior_citizen_id=''),
            models.Q(user__pwd_id__isnull=True) | models.Q(user__pwd_id='')
        ).order_by('created_at')

        # Check if current user is priority
        is_priority = self.is_priority_user()

        # START RECALCULATING: All queue numbers reset
        queue_num = 1

        # PHASE 1: Assign numbers to ALL existing priority users
        for order in priority_orders:
            order.queue_number = queue_num
            order.save(update_fields=['queue_number'])
            queue_num += 1

        # PHASE 2: If current user is priority, insert them NOW
        if is_priority:
            self.queue_number = queue_num
            queue_num += 1

        # PHASE 3: Assign numbers to ALL regular users (they get pushed down)
        for order in regular_orders:
            order.queue_number = queue_num
            order.save(update_fields=['queue_number'])
            queue_num += 1

        # Save self with correct queue number
        if not is_priority:
            self.queue_number = queue_num

        self.save(update_fields=['queue_number'])

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
        Checks if senior_citizen_id or pwd_id files are actually uploaded.
        """
        has_senior_id = bool(self.user.senior_citizen_id and self.user.senior_citizen_id.name)
        has_pwd_id = bool(self.user.pwd_id and self.user.pwd_id.name)
        return has_senior_id or has_pwd_id


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    special_request = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "tblorderitems"

    def __str__(self):
        return f"{self.medicine.name} × {self.quantity}"