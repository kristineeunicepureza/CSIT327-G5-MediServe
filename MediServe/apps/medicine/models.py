from django.db import models
from django.utils import timezone
from datetime import date


class Medicine(models.Model):
    # Medicine Types
    PRESCRIPTION_TYPE_CHOICES = [
        ('non_prescription', 'Non-Prescription (Over-the-Counter)'),
        ('prescription', 'Prescription Required'),
    ]

    # Order Limit Types
    ORDER_LIMIT_CHOICES = [
        ('3_days', '3 Days Supply'),
        ('1_week', '1 Week Supply'),
    ]

    # Existing fields
    name = models.CharField(max_length=255)
    brand = models.CharField(max_length=255, null=True, blank=True)
    category = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # NEW: Prescription and ordering restrictions
    prescription_type = models.CharField(
        max_length=20,
        choices=PRESCRIPTION_TYPE_CHOICES,
        default='non_prescription',
        help_text='Specify if this medicine requires a prescription'
    )
    order_limit = models.CharField(
        max_length=10,
        choices=ORDER_LIMIT_CHOICES,
        default='1_week',
        help_text='Maximum supply duration that can be ordered at once'
    )
    is_orderable = models.BooleanField(
        default=True,
        help_text='Only non-prescription medicines can be ordered online'
    )

    # Existing archive fields
    status = models.CharField(
        max_length=20,
        choices=[('active', 'Active'), ('archived', 'Archived')],
        default='active'
    )
    archived_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'tblmedicine'
        managed = True

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Override save to automatically set is_orderable based on prescription_type"""
        # Only non-prescription medicines can be ordered online
        self.is_orderable = (self.prescription_type == 'non_prescription')
        super().save(*args, **kwargs)

    def get_max_order_quantity(self):
        """Get maximum quantity that can be ordered based on order_limit"""
        if self.order_limit == '3_days':
            return 3  # 3 days supply
        elif self.order_limit == '1_week':
            return 7  # 7 days supply (1 week)
        return 7  # default to 1 week

    def can_be_ordered(self):
        """Check if this medicine can be ordered online"""
        return self.is_orderable and self.prescription_type == 'non_prescription' and self.status == 'active'

    @property
    def total_stock(self):
        """Get total available stock across all ACTIVE batches"""
        from django.db.models import Sum
        total = self.medicinebatch_set.filter(
            status='active'  # Only count active batches
        ).aggregate(
            total=Sum('quantity_available')
        )['total']
        return total or 0

    def get_next_expiring_batch(self):
        """Get the batch with earliest expiry date (FEFO) - only active batches"""
        return self.medicinebatch_set.filter(
            quantity_available__gt=0,
            status='active'  # Only consider active batches
        ).order_by('expiry_date', 'batch_id').first()

    # NEW: Archive methods
    def archive(self):
        """Archive this medicine and all its batches"""
        self.status = 'archived'
        self.archived_at = timezone.now()
        self.save()

        # Also archive all batches of this medicine
        self.medicinebatch_set.all().update(
            status='archived',
            archived_at=timezone.now()
        )

    def restore(self):
        """Restore this medicine and all its batches"""
        self.status = 'active'
        self.archived_at = None
        self.save()

        # Also restore all batches of this medicine
        self.medicinebatch_set.all().update(
            status='active',
            archived_at=None
        )


class MedicineBatch(models.Model):
    # Existing fields
    batch_id = models.CharField(max_length=100, db_index=True)
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)

    expiry_date = models.DateField()
    date_received = models.DateField()

    quantity_received = models.IntegerField(default=0)
    quantity_available = models.IntegerField(default=0)
    quantity_dispensed = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # NEW: Archive fields
    status = models.CharField(
        max_length=20,
        choices=[('active', 'Active'), ('archived', 'Archived')],
        default='active'
    )
    archived_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'tblmedicine_batch'
        managed = True
        ordering = ['expiry_date', 'batch_id']
        unique_together = [['batch_id', 'medicine']]

    def __str__(self):
        return f"{self.batch_id} - {self.medicine.name}"

    @property
    def is_expiring_soon(self):
        if not self.expiry_date:
            return False
        days_until_expiry = (self.expiry_date - timezone.now().date()).days
        return 0 < days_until_expiry <= 30

    @property
    def is_expired(self):
        """Check if batch is expired"""
        if not self.expiry_date:
            return False
        return self.expiry_date < date.today()

    def dispense(self, quantity):
        """Dispense quantity from this batch"""
        if quantity > self.quantity_available:
            return False

        self.quantity_available -= quantity
        self.quantity_dispensed += quantity
        self.save()
        return True

    def get_stock_percentage(self):
        """Get percentage of original stock remaining"""
        if self.quantity_received == 0:
            return 0
        return (self.quantity_available / self.quantity_received) * 100

    # NEW: Archive methods
    def archive(self):
        """Archive this batch"""
        self.status = 'archived'
        self.archived_at = timezone.now()
        self.save()

    def restore(self):
        """Restore this batch"""
        self.status = 'active'
        self.archived_at = None
        self.save()

    # NEW: Auto-archive expired batches
    @classmethod
    def auto_archive_expired(cls):
        """Auto-archive all expired batches"""
        expired_batches = cls.objects.filter(
            expiry_date__lt=date.today(),
            status='active'
        )
        count = expired_batches.count()
        expired_batches.update(
            status='archived',
            archived_at=timezone.now()
        )
        return count