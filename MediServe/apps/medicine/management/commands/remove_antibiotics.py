# File: apps/medicine/management/commands/remove_antibiotics.py

from django.core.management.base import BaseCommand
from django.db.models import Q
from apps.medicine.models import Medicine, MedicineBatch


class Command(BaseCommand):
    help = 'Remove or archive all medicines containing "antibiotic" in name, category, or description'

    def add_arguments(self, parser):
        parser.add_argument(
            '--archive',
            action='store_true',
            help='Archive antibiotics instead of deleting them',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be removed without actually removing',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        archive_mode = options['archive']

        # Find all medicines with "antibiotic" in name, category, or description
        antibiotic_medicines = Medicine.objects.filter(
            Q(name__icontains='antibiotic') |
            Q(category__icontains='antibiotic') |
            Q(description__icontains='antibiotic')
        )

        count = antibiotic_medicines.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS('✅ No antibiotics found in the database.'))
            return

        self.stdout.write(self.style.WARNING(f'\n🔍 Found {count} medicine(s) containing "antibiotic":\n'))

        # Display found medicines
        for medicine in antibiotic_medicines:
            self.stdout.write(f'  - ID: {medicine.id}')
            self.stdout.write(f'    Name: {medicine.name}')
            self.stdout.write(f'    Category: {medicine.category or "N/A"}')
            self.stdout.write(f'    Status: {medicine.status}')

            # Get batches
            batches = MedicineBatch.objects.filter(medicine=medicine)
            self.stdout.write(f'    Batches: {batches.count()}')

            # Get total stock
            self.stdout.write(f'    Total Stock: {medicine.total_stock}\n')

        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  DRY RUN MODE - No changes made'))
            if archive_mode:
                self.stdout.write('   Would ARCHIVE these medicines and their batches')
            else:
                self.stdout.write('   Would DELETE these medicines and their batches')
            return

        # Confirm action
        confirm = input(
            f'\n⚠️  This will {"ARCHIVE" if archive_mode else "DELETE"} {count} medicine(s) and all their batches. Continue? (yes/no): ')

        if confirm.lower() != 'yes':
            self.stdout.write(self.style.ERROR('❌ Operation cancelled.'))
            return

        # Perform action
        total_batches = 0

        for medicine in antibiotic_medicines:
            batch_count = MedicineBatch.objects.filter(medicine=medicine).count()
            total_batches += batch_count

            if archive_mode:
                # Archive the medicine (this also archives all batches)
                medicine.archive()
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Archived: {medicine.name} ({batch_count} batches)')
                )
            else:
                # Delete the medicine (this also deletes all batches due to CASCADE)
                medicine_name = medicine.name
                medicine.delete()
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Deleted: {medicine_name} ({batch_count} batches)')
                )

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Successfully {"archived" if archive_mode else "deleted"} '
            f'{count} medicine(s) and {total_batches} batch(es).'
        ))

        if archive_mode:
            self.stdout.write(self.style.WARNING(
                '\nℹ️  Archived items can be viewed in the admin panel and restored if needed.'
            ))

