from django.core.management.base import BaseCommand
from django.db.models import Q
from apps.orders.models import Order


class Command(BaseCommand):
    help = 'Recalculate all queue numbers for Pending/Processing orders'

    def handle(self, *args, **options):
        # Get all Pending/Processing orders
        all_orders = Order.objects.filter(
            status__in=['Pending', 'Processing']
        ).order_by('created_at')

        # Separate priority and regular users
        # Priority users have uploaded senior_citizen_id OR pwd_id files (not empty strings)
        priority_orders = all_orders.filter(
            Q(user__senior_citizen_id__isnull=False, user__senior_citizen_id__gt='') |
            Q(user__pwd_id__isnull=False, user__pwd_id__gt='')
        ).order_by('created_at')

        regular_orders = all_orders.filter(
            Q(user__senior_citizen_id__isnull=True) | Q(user__senior_citizen_id=''),
            Q(user__pwd_id__isnull=True) | Q(user__pwd_id='')
        ).order_by('created_at')

        queue_num = 1

        # Assign queue numbers to priority users first
        self.stdout.write(self.style.SUCCESS('\n=== PRIORITY USERS (Senior Citizen/Person with Disability) ==='))
        for order in priority_orders:
            order.queue_number = queue_num
            order.save(update_fields=['queue_number'])
            self.stdout.write(
                f'✅ Order #{order.id} ({order.user.full_name}) → Queue #{queue_num}'
            )
            queue_num += 1

        # Assign queue numbers to regular users
        self.stdout.write(self.style.SUCCESS('\n=== REGULAR USERS ==='))
        for order in regular_orders:
            order.queue_number = queue_num
            order.save(update_fields=['queue_number'])
            self.stdout.write(
                f'✅ Order #{order.id} ({order.user.full_name}) → Queue #{queue_num}'
            )
            queue_num += 1

        # Clear queue numbers for other statuses
        Order.objects.filter(
            status__in=['Shipped', 'Completed', 'Cancelled']
        ).update(queue_number=None)

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Successfully recalculated queue numbers for {queue_num - 1} orders!'
        ))
