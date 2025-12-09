from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum
from django.db import transaction
from django.http import JsonResponse
from datetime import date, datetime, timedelta
from .models import Medicine, MedicineBatch
from .forms import MedicineForm, MedicineBatchEditForm


# -------------------------------------------------------------------
# UPDATED: Get Next Batch ID - EXCLUDES ARCHIVED BATCHES
# -------------------------------------------------------------------
@login_required
def get_next_batch_id(request):
    """
    Return the next available batch ID in sequence.
    EXCLUDES ARCHIVED BATCHES - archived batch numbers cannot be reused.

    Example: If BATCH-007 is archived, the next batch will be BATCH-008
    """
    # Check if there are ANY batches (including archived) to continue numbering
    all_batches_ever = MedicineBatch.objects.filter(
        batch_id__startswith='BATCH-'
    ).values_list('batch_id', flat=True)

    if all_batches_ever:
        # Extract numbers from ALL batches (active + archived)
        numbers = []
        for batch in all_batches_ever:
            try:
                num = int(batch.split('-')[1])
                numbers.append(num)
            except (IndexError, ValueError):
                continue

        if numbers:
            # Next batch ID is max + 1 (includes archived in the count)
            next_number = max(numbers) + 1
        else:
            next_number = 1
    else:
        next_number = 1

    next_batch_id = f'BATCH-{next_number:03d}'
    return JsonResponse({'next_batch_id': next_batch_id})


# -------------------------------------------------------------------
# Admin: Medicine Stock (FEFO Batch View) - UPDATED BATCH ID GENERATION
# -------------------------------------------------------------------
@login_required
def medicine_stock(request):
    """
    Medicine stock management (FEFO batch view) with archive system.
    Shows only ACTIVE batches.

    UPDATED: Batch ID generation excludes archived batches
    """

    # Get all ACTIVE batches sorted by expiry date (FEFO)
    batches = MedicineBatch.objects.filter(
        status='active'
    ).select_related('medicine').order_by('expiry_date', 'batch_id')

    # Get all active medicines for reference
    all_medicines = Medicine.objects.filter(status='active').order_by('name')

    # Search functionality
    search_query = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    stock_filter = request.GET.get('stock', '')

    if search_query:
        batches = batches.filter(
            Q(medicine__name__icontains=search_query) |
            Q(medicine__brand__icontains=search_query) |
            Q(medicine__category__icontains=search_query) |
            Q(batch_id__icontains=search_query)
        )

    if category_filter:
        batches = batches.filter(medicine__category__iexact=category_filter)

    if stock_filter:
        if stock_filter == 'low':
            batches = batches.filter(quantity_available__lte=10)
        elif stock_filter == 'medium':
            batches = batches.filter(quantity_available__gt=10, quantity_available__lte=50)
        elif stock_filter == 'high':
            batches = batches.filter(quantity_available__gt=50)

    # Get unique categories for filter dropdown (from active medicines)
    categories = Medicine.objects.filter(
        status='active'
    ).values_list('category', flat=True).distinct()

    # Count archived batches for header button
    archived_count_display = MedicineBatch.objects.filter(status='archived').count()

    # Add today's date for expired badge check
    today = date.today()

    # Handle POST - Add New Batch
    if request.method == 'POST':
        try:
            # ✅ UPDATED: AUTO-GENERATE BATCH ID - Continues numbering after archived batches
            # Example: If BATCH-007 is archived, next will be BATCH-008

            # Get ALL batch IDs (including archived ones)
            all_batches_ever = MedicineBatch.objects.filter(
                batch_id__startswith='BATCH-'
            ).values_list('batch_id', flat=True)

            if all_batches_ever:
                # Extract numbers from ALL batches (active + archived)
                numbers = []
                for batch in all_batches_ever:
                    try:
                        num = int(batch.split('-')[1])
                        numbers.append(num)
                    except (IndexError, ValueError):
                        continue

                if numbers:
                    # Next batch ID is max + 1 (includes archived in the count)
                    next_number = max(numbers) + 1
                else:
                    next_number = 1
            else:
                next_number = 1

            batch_id = f'BATCH-{next_number:03d}'

            # Get form data
            expiry_date_str = request.POST.get('expiry_date', '').strip()
            date_received_str = request.POST.get('date_received', '').strip()
            medicine_name = request.POST.get('medicine_name', '').strip()
            brand = request.POST.get('brand', '').strip()
            category = request.POST.get('category', '').strip()
            description = request.POST.get('description', '').strip()
            quantity_str = request.POST.get('quantity', '').strip()

            # Validation
            if not date_received_str:
                messages.error(request, '❌ Date Received is required!')
                return redirect('medicine_stock')

            if not expiry_date_str:
                messages.error(request, '❌ Expiry Date is required!')
                return redirect('medicine_stock')

            if not medicine_name:
                messages.error(request, '❌ Medicine Name is required!')
                return redirect('medicine_stock')

            if not quantity_str:
                messages.error(request, '❌ Quantity is required!')
                return redirect('medicine_stock')

            # Convert dates
            try:
                expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
                date_received = datetime.strptime(date_received_str, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, '❌ Invalid date format! Please use the date picker.')
                return redirect('medicine_stock')

            # Date validation
            if date_received > today:
                messages.error(
                    request,
                    f'❌ Date Received cannot be in the future! You entered: {date_received.strftime("%B %d, %Y")} but today is {today.strftime("%B %d, %Y")}.'
                )
                return redirect('medicine_stock')

            if expiry_date <= today:
                messages.error(
                    request,
                    f'❌ Expiry Date must be in the future! You entered: {expiry_date.strftime("%B %d, %Y")} but today is {today.strftime("%B %d, %Y")}.'
                )
                return redirect('medicine_stock')

            if expiry_date <= date_received:
                messages.error(
                    request,
                    f'❌ Expiry Date ({expiry_date.strftime("%B %d, %Y")}) must be after Date Received ({date_received.strftime("%B %d, %Y")})!'
                )
                return redirect('medicine_stock')

            # Validate quantity
            try:
                quantity = int(quantity_str)
                if quantity <= 0:
                    messages.error(request, '❌ Quantity must be greater than 0!')
                    return redirect('medicine_stock')
            except ValueError:
                messages.error(request, '❌ Invalid quantity! Please enter a valid number.')
                return redirect('medicine_stock')

            # Create batch with transaction
            with transaction.atomic():
                # Get or create medicine (case-insensitive check)
                medicine = Medicine.objects.filter(
                    name__iexact=medicine_name,
                    status='active'
                ).first()

                if medicine:
                    # Medicine exists - update info if new data provided
                    updated_fields = []

                    if brand and brand != medicine.brand:
                        medicine.brand = brand
                        updated_fields.append('brand')

                    if category and category != medicine.category:
                        medicine.category = category
                        updated_fields.append('category')

                    if description and description != medicine.description:
                        medicine.description = description
                        updated_fields.append('description')

                    if updated_fields:
                        medicine.save()
                        messages.info(
                            request,
                            f'ℹ️ Updated {", ".join(updated_fields)} for existing medicine "{medicine.name}".'
                        )
                else:
                    # Create new medicine (automatically active)
                    medicine = Medicine.objects.create(
                        name=medicine_name,
                        brand=brand if brand else None,
                        category=category if category else None,
                        description=description if description else None,
                        status='active'
                    )
                    messages.info(request, f'ℹ️ New medicine "{medicine.name}" created.')

                # Create batch entry (automatically active)
                new_batch = MedicineBatch.objects.create(
                    batch_id=batch_id,
                    medicine=medicine,
                    expiry_date=expiry_date,
                    date_received=date_received,
                    quantity_received=quantity,
                    quantity_available=quantity,
                    quantity_dispensed=0,
                    status='active'
                )

                messages.success(
                    request,
                    f'✅ Batch "{batch_id}" added successfully!\n'
                    f'Medicine: {medicine.name}\n'
                    f'Quantity: {quantity} units\n'
                    f'Expiry: {expiry_date.strftime("%B %d, %Y")}'
                )

        except Exception as e:
            messages.error(request, f'❌ Unexpected error: {str(e)}')
            print(f"Error in medicine_stock POST: {e}")

        return redirect('medicine_stock')

    # GET request - render the page
    return render(request, 'medicine_stock.html', {
        'batches': batches,
        'all_medicines': all_medicines,
        'categories': categories,
        'search_query': search_query,
        'category_filter': category_filter,
        'stock_filter': stock_filter,
        'archived_count': archived_count_display,
        'today': today,
    })


# -------------------------------------------------------------------
# UPDATED: Archived Medicines View - With category filter and today
# -------------------------------------------------------------------
@login_required
def archived_medicines(request):
    """
    Display archived medicine batches.
    Admin only.
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, '❌ Access denied. Admins only.')
        return redirect('main_menu')

    # Get all archived batches
    archived_batches = MedicineBatch.objects.filter(
        status='archived'
    ).select_related('medicine').order_by('expiry_date', '-archived_at')

    # Search functionality
    search_query = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')

    if search_query:
        archived_batches = archived_batches.filter(
            Q(medicine__name__icontains=search_query) |
            Q(medicine__brand__icontains=search_query) |
            Q(batch_id__icontains=search_query)
        )

    if category_filter:
        archived_batches = archived_batches.filter(medicine__category__iexact=category_filter)

    # Get unique categories for filter dropdown
    categories = Medicine.objects.filter(
        id__in=MedicineBatch.objects.filter(status='archived').values_list('medicine_id', flat=True)
    ).values_list('category', flat=True).distinct()

    context = {
        'archived_batches': archived_batches,
        'total_archived': archived_batches.count(),
        'search_query': search_query,
        'category_filter': category_filter,
        'categories': categories,
        'today': date.today(),
    }

    return render(request, 'admin_archived_medicines.html', context)


# -------------------------------------------------------------------
# Archive Batch
# -------------------------------------------------------------------
@login_required
def archive_batch(request, batch_id):
    """
    Archive a medicine batch.
    Admin only.
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, '❌ Access denied. Admins only.')
        return redirect('main_menu')

    if request.method == 'POST':
        try:
            batch = get_object_or_404(MedicineBatch, id=batch_id, status='active')

            # Check if batch has pending orders
            from apps.orders.models import OrderItem
            pending_orders = OrderItem.objects.filter(
                medicine=batch.medicine,
                order__status__in=['Pending', 'Processing', 'Shipped']
            ).exists()

            if pending_orders:
                messages.warning(
                    request,
                    f'⚠️ Cannot archive {batch.medicine.name} (Batch {batch.batch_id}) - it has pending orders. Complete or cancel those orders first.'
                )
                return redirect('medicine_stock')

            # Archive the batch
            batch.archive()

            messages.success(
                request,
                f'🗄️ Batch {batch.batch_id} ({batch.medicine.name}) has been archived permanently.'
            )

        except MedicineBatch.DoesNotExist:
            messages.error(request, '❌ Batch not found!')
        except Exception as e:
            messages.error(request, f'❌ Error archiving batch: {str(e)}')

    return redirect('medicine_stock')


# -------------------------------------------------------------------
# UPDATED: Delete Archived Batch (Permanent)
# -------------------------------------------------------------------
@login_required
def delete_archived_batch(request, batch_id):
    """
    Permanently delete an archived batch from the database.
    This is irreversible.
    Admin only.
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, '❌ Access denied. Admins only.')
        return redirect('main_menu')

    if request.method == 'POST':
        try:
            batch = get_object_or_404(MedicineBatch, id=batch_id, status='archived')

            medicine_name = batch.medicine.name
            batch_number = batch.batch_id

            # Permanently delete the batch
            batch.delete()

            messages.success(
                request,
                f'🗑️ Batch {batch_number} ({medicine_name}) has been permanently deleted from the database.'
            )

        except MedicineBatch.DoesNotExist:
            messages.error(request, '❌ Batch not found or not archived!')
        except Exception as e:
            messages.error(request, f'❌ Error deleting batch: {str(e)}')

    return redirect('archived_medicines')


# -------------------------------------------------------------------
# Edit Medicine (Batch Information)
# -------------------------------------------------------------------
@login_required
def edit_medicine(request, id):
    """
    Edit medicine batch details.
    Admin only.
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, '❌ Access denied. Admins only.')
        return redirect('main_menu')

    batch = get_object_or_404(MedicineBatch, id=id)
    medicine = batch.medicine

    if request.method == 'POST':
        # Update medicine info
        medicine.name = request.POST.get('name', '').strip()
        medicine.brand = request.POST.get('brand', '').strip()
        medicine.category = request.POST.get('category', '').strip()
        medicine.description = request.POST.get('description', '').strip()

        # Update batch info
        try:
            # Get dates
            expiry_date_str = request.POST.get('expiry_date', '').strip()
            date_received_str = request.POST.get('date_received', '').strip()

            if expiry_date_str:
                expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
                batch.expiry_date = expiry_date

            if date_received_str:
                date_received = datetime.strptime(date_received_str, '%Y-%m-%d').date()
                batch.date_received = date_received

            # Get quantities
            quantity_received = int(request.POST.get('quantity_received', batch.quantity_received))
            quantity_available = int(request.POST.get('quantity_available', batch.quantity_available))

            # Validate
            if quantity_available > quantity_received:
                messages.error(request, '❌ Available quantity cannot exceed received quantity!')
                return redirect('edit_medicine', id=id)

            batch.quantity_received = quantity_received
            batch.quantity_available = quantity_available
            batch.quantity_dispensed = quantity_received - quantity_available

            # Save changes
            medicine.save()
            batch.save()

            messages.success(
                request,
                f'✅ {medicine.name} (Batch {batch.batch_id}) updated successfully!'
            )
            return redirect('medicine_stock')

        except ValueError as e:
            messages.error(request, f'❌ Invalid input: {str(e)}')
            return redirect('edit_medicine', id=id)
        except Exception as e:
            messages.error(request, f'❌ Error updating: {str(e)}')
            return redirect('edit_medicine', id=id)

    # GET request - show form
    return render(request, 'edit_medicine.html', {
        'medicine': medicine,
        'batch': batch,
    })


# -------------------------------------------------------------------
# Edit Batch (Placeholder - redirects to edit_medicine)
# -------------------------------------------------------------------
@login_required
def edit_batch(request, batch_id):
    """
    Edit batch functionality - redirect to edit_medicine.
    """
    try:
        batch = MedicineBatch.objects.get(batch_id=batch_id)
        return redirect('edit_medicine', id=batch.id)
    except MedicineBatch.DoesNotExist:
        messages.error(request, "❌ Batch not found!")
        return redirect('medicine_stock')


# -------------------------------------------------------------------
# DEPRECATED: Delete Medicine Batch (replaced with archive)
# -------------------------------------------------------------------
@login_required
def delete_medicine(request, id):
    """
    DEPRECATED: Delete medicine batch.
    Now redirects to archive functionality.
    """
    messages.info(
        request,
        'ℹ️ Delete functionality has been replaced with Archive. Use the Archive button instead.'
    )
    return redirect('medicine_stock')


# -------------------------------------------------------------------
# UPDATED: Medicine Distribution History - REMOVED RECIPIENT FILTER
# -------------------------------------------------------------------
@login_required
def medicine_distribution_history(request):
    """
    View medicine distribution history.
    Only shows distributions to NON-ADMIN users (regular community members).
    Admin only view.

    UPDATED:
    - Changed "Unique Recipients" to "Recipients"
    - Removed recipient filter dropdown
    - Only search bar remains for filtering recipients
    """
    from apps.orders.models import Order, OrderItem
    from apps.accounts.models import Account

    # Check if user is admin
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, '❌ Access denied. Admins only.')
        return redirect('main_menu')

    # Get all completed orders - EXCLUDE orders from admin users
    completed_orders = Order.objects.filter(
        status='Completed',
        user__is_staff=False,
        user__is_superuser=False
    ).select_related('user').prefetch_related('items__medicine').order_by('-completed_at')

    # Apply filters
    search_query = request.GET.get('search', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    medicine_filter = request.GET.get('medicine', '')
    # ❌ REMOVED: user_filter = request.GET.get('user', '')

    # Search by user name, email, or medicine name
    if search_query:
        completed_orders = completed_orders.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(items__medicine__name__icontains=search_query)
        ).distinct()

    # Date range filter
    if date_from:
        completed_orders = completed_orders.filter(completed_at__gte=date_from)
    if date_to:
        # Add one day to include the entire end date
        date_to_obj = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
        completed_orders = completed_orders.filter(completed_at__lt=date_to_obj)

    # Medicine filter
    if medicine_filter:
        completed_orders = completed_orders.filter(items__medicine__id=medicine_filter).distinct()

    # ❌ REMOVED: User filter
    # if user_filter:
    #     completed_orders = completed_orders.filter(user__id=user_filter)

    # Get statistics - ONLY for non-admin users
    total_distributions = completed_orders.count()
    total_medicines_distributed = OrderItem.objects.filter(
        order__status='Completed',
        order__user__is_staff=False,
        order__user__is_superuser=False
    ).aggregate(total=Sum('quantity'))['total'] or 0

    # ✅ CHANGED: "unique_recipients" → "recipients_count" for clarity
    recipients_count = completed_orders.values('user').distinct().count()

    # Get most distributed medicines - ONLY for non-admin users
    top_medicines = OrderItem.objects.filter(
        order__status='Completed',
        order__user__is_staff=False,
        order__user__is_superuser=False
    ).values('medicine__name').annotate(
        total_qty=Sum('quantity')
    ).order_by('-total_qty')[:5]

    # Get all medicines for filter dropdown
    all_medicines = Medicine.objects.all().order_by('name')

    # ❌ REMOVED: Get all non-admin users for filter dropdown
    # all_users = Account.objects.filter(
    #     is_staff=False,
    #     is_superuser=False
    # ).order_by('first_name', 'last_name')

    context = {
        'completed_orders': completed_orders,
        'total_distributions': total_distributions,
        'total_medicines_distributed': total_medicines_distributed,
        'recipients_count': recipients_count,  # ✅ Changed variable name
        'top_medicines': top_medicines,
        'all_medicines': all_medicines,
        # ❌ REMOVED: 'all_users': all_users,
        'search_query': search_query,
        'date_from': date_from,
        'date_to': date_to,
        'medicine_filter': medicine_filter,
        # ❌ REMOVED: 'user_filter': user_filter,
    }

    return render(request, 'medicine_distribution_history.html', context)


# -------------------------------------------------------------------
# Medicine List (Public Browse) - ONLY SHOW ACTIVE MEDICINES
# -------------------------------------------------------------------
@login_required
def medicine_list(request):
    """
    Display list of medicines with search and filter capabilities.
    In-stock medicines appear FIRST, out-of-stock medicines appear LAST.
    ONLY SHOWS ACTIVE MEDICINES.
    """
    # Get all ACTIVE medicines only
    medicines = Medicine.objects.filter(status='active')

    # Get unique categories for filter dropdown (from active medicines)
    categories = Medicine.objects.filter(
        status='active'
    ).values_list('category', flat=True).distinct().order_by('category')
    categories = [cat for cat in categories if cat]

    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        medicines = medicines.filter(
            Q(name__icontains=search_query) | Q(brand__icontains=search_query)
        )

    # Category filter
    category_filter = request.GET.get('category', '')
    if category_filter:
        medicines = medicines.filter(category=category_filter)

    # Stock filter
    stock_filter = request.GET.get('stock', '')

    # Convert to list and add batch information for each medicine
    medicines_list = []
    for medicine in medicines:
        # Only get ACTIVE batches
        medicine.batch_list = MedicineBatch.objects.filter(
            medicine=medicine,
            quantity_available__gt=0,
            status='active'
        ).order_by('expiry_date', 'batch_id').values_list('batch_id', flat=True).distinct()
        medicines_list.append(medicine)

    # Apply stock filter
    if stock_filter:
        if stock_filter == 'in-stock':
            medicines_list = [m for m in medicines_list if m.total_stock > 10]
        elif stock_filter == 'low-stock':
            medicines_list = [m for m in medicines_list if 0 < m.total_stock <= 10]
        elif stock_filter == 'out-of-stock':
            medicines_list = [m for m in medicines_list if m.total_stock == 0]

    # Sort: In-stock medicines FIRST, out-of-stock LAST
    medicines_list.sort(key=lambda m: (m.total_stock == 0, m.name.lower()))

    context = {
        'medicines': medicines_list,
        'categories': categories,
        'search_query': search_query,
        'category_filter': category_filter,
        'stock_filter': stock_filter,
    }

    return render(request, 'medicine_list.html', context)


# -------------------------------------------------------------------
# Medicine Info Page - ONLY SHOW IF ACTIVE
# -------------------------------------------------------------------
@login_required
def medicine_info(request, medicine_id):
    """Medicine details page - only show if active."""
    medicine = get_object_or_404(Medicine, id=medicine_id, status='active')
    return render(request, 'medicine_info.html', {'medicine': medicine})


# -------------------------------------------------------------------
# Add medicine to order - ONLY ACTIVE MEDICINES
# -------------------------------------------------------------------
@login_required
def add_to_order(request, medicine_id):
    """Add medicine to user's order (cart) - only if active."""
    from apps.orders.models import Order, OrderItem
    from django.utils import timezone

    medicine = get_object_or_404(Medicine, id=medicine_id, status='active')

    if request.method == "POST":
        quantity = int(request.POST.get("quantity", 1))
        special_request = request.POST.get("special_request", "")

        # Check stock using total_stock property (which now only counts active batches)
        if quantity > medicine.total_stock:
            messages.warning(
                request,
                f"⚠️ Only {medicine.total_stock} units available in stock."
            )
            return redirect("medicine_info", medicine_id=medicine.id)

        # Get or create pending order (cart)
        order, created = Order.objects.get_or_create(
            user=request.user,
            status="Pending",
            defaults={"created_at": timezone.now()}
        )

        # Add or update order item
        item, item_created = OrderItem.objects.get_or_create(
            order=order,
            medicine=medicine,
            defaults={"quantity": quantity, "special_request": special_request}
        )

        if not item_created:
            item.quantity += quantity
            if special_request:
                item.special_request = special_request
            item.save()

        messages.success(
            request,
            f"✅ Added {quantity} × {medicine.name} to your order."
        )

        # Redirect to order list to review cart
        return redirect("order_list")

    # GET request - show medicine info page
    return redirect("medicine_info", medicine_id=medicine.id)


# -------------------------------------------------------------------
# Medicine History and Records (Placeholder views)
# -------------------------------------------------------------------
@login_required
def medicine_history(request):
    """Medicine history page."""
    return render(request, 'medicine_history.html')


@login_required
def medicine_records(request):
    """Medicine records page."""
    return render(request, 'medicine_records.html')