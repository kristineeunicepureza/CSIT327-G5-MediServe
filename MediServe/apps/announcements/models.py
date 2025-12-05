from django.db import models
from django.utils import timezone
from datetime import timedelta


class Announcement(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("archived", "Archived"),
    ]

    title = models.CharField(max_length=255)
    content = models.TextField()
    date_posted = models.DateTimeField(auto_now_add=True)

    # NEW FIELD — controls whether announcement is visible or archived
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active"
    )

    # Optional: track when it was archived
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'tblannouncements'
        managed = True

    def __str__(self):
        return self.title

    # 🔄 AUTO-ARCHIVE LOGIC (30 DAYS)
    @staticmethod
    def auto_archive_old_announcements():
        cutoff_date = timezone.now() - timedelta(days=30)
        Announcement.objects.filter(
            status="active",
            date_posted__lt=cutoff_date
        ).update(status="archived", archived_at=timezone.now())
