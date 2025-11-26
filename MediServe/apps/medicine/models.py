from django.db import models
from django.utils import timezone


class Medicine(models.Model):
    name = models.CharField(max_length=255)
    brand = models.CharField(max_length=255, null=True, blank=True)
    category = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tblmedicine'
        managed = True

    def __str__(self):
        return self.name

    @property
    def total_stock(self):
        """Get total available stock across all batches"""
        from django.db.models import Sum
        total = self.medicinebatch_set.aggregate(
            total=Sum('quantity_available')
        )['total']
        return total or 0

    def get_next_expiring_batch(self):
        """Get the batch with earliest expiry date (FEFO)"""
        return self.medicinebatch_set.filter(
            quantity_available__gt=0
        ).order_by('expiry_date', 'batch_id').first()


class MedicineBatch(models.Model):
    batch_id = models.CharField(max_length=100, db_index=True)
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)

    expiry_date = models.DateField()
    date_received = models.DateField()

    quantity_received = models.IntegerField(default=0)
    quantity_available = models.IntegerField(default=0)
    quantity_dispensed = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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