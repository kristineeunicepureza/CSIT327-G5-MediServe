from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.db import transaction
from .models import Medicine, MedicineBatch


# -------------------------------------------------------------------
# Medicine History Page
# -------------------------------------------------------------------
@login_required
def medicine_history(request):
    return render(request, 'medicine_history.html')


# -------------------------------------------------------------------
# Admin: Medicine Stock (FEFO Batch View)
# -------------------------------------------------------------------
@login_required
def medicine_stock(request):
    """Medicine stock management (FEFO batch view)."""

    # Get all batches sorted by expiry date (FEFO)
    batches = MedicineBatch.objects.select_related('medicine').order_by('expiry_date', 'batch_id')

    # Get all medicines for reference
    all_medicines = Medicine.objects.all().order_by('name')

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

    # Get unique categories for filter dropdown
    categories = Medicine.objects.values_list('category', flat=True).distinct()

    # Handle POST - Add New Batch with Multiple Medicines
    if request.method == 'POST':
        try:
            batch_id = request.POST.get('batch_id')
            expiry_date = request.POST.get('expiry_date')
            date_received = request.POST.get('date_received')

            medicine_names = request.POST.getlist('medicine_name[]')
            brands = request.POST.getlist('brand[]')
            categories = request.POST.getlist('category[]')
            descriptions = request.POST.getlist('description[]')
            quantities = request.POST.getlist('quantity[]')

            # Validation
            if not batch_id or not expiry_date or not date_received:
                messages.error(request, '⚠️ Please fill all batch information fields.')
                return redirect('medicine_stock')

            if not medicine_names or len(medicine_names) == 0:
                messages.error(request, '⚠️ Please add at least one medicine to the batch.')
                return redirect('medicine_stock')

            # Check for duplicate batch_id
            if MedicineBatch.objects.filter(batch_id=batch_id).exists():
                messages.error(request, f'⚠️ Batch ID "{batch_id}" already exists. Please use a unique Batch ID.')
                return redirect('medicine_stock')

            # Use transaction to ensure all-or-nothing save
            with transaction.atomic():
                created_count = 0

                for i, medicine_name in enumerate(medicine_names):
                    if not medicine_name or not medicine_name.strip():
                        continue

                    brand = brands[i] if i < len(brands) else ''
                    category = categories[i] if i < len(categories) else ''
                    description = descriptions[i] if i < len(descriptions) else ''
                    quantity = int(quantities[i]) if i < len(quantities) and quantities[i] else 0

                    if quantity <= 0:
                        continue

                    # Get or create medicine
                    medicine, created = Medicine.objects.get_or_create(
                        name__iexact=medicine_name.strip(),
                        defaults={
                            'name': medicine_name.strip(),
                            'brand': brand.strip() if brand else None,
                            'category': category.strip() if category else None,
                            'description': description.strip() if description else None,
                        }
                    )

                    # Update medicine info if it already exists and new data provided
                    if not created:
                        updated = False
                        if brand and brand.strip():
                            medicine.brand = brand.strip()
                            updated = True
                        if category and category.strip():
                            medicine.category = category.strip()
                            updated = True
                        if description and description.strip():
                            medicine.description = description.strip()
                            updated = True
                        if updated:
                            medicine.save()

                    # Check if this medicine already exists in this batch
                    if MedicineBatch.objects.filter(batch_id=batch_id, medicine=medicine).exists():
                        messages.warning(request, f'⚠️ {medicine.name} is already in batch {batch_id}. Skipped.')
                        continue

                    # Create batch entry
                    MedicineBatch.objects.create(
                        batch_id=batch_id,
                        medicine=medicine,
                        expiry_date=expiry_date,
                        date_received=date_received,
                        quantity_received=quantity,
                        quantity_available=quantity,
                        quantity_dispensed=0
                    )
                    created_count += 1

                if created_count > 0:
                    messages.success(request,
                                     f'✅ Batch "{batch_id}" added successfully with {created_count} medicine(s)!')
                else:
                    messages.error(request, '⚠️ No valid medicines were added to the batch.')

        except Exception as e:
            messages.error(request, f'⚠️ Error adding batch: {str(e)}')

        return redirect('medicine_stock')

    return render(request, 'medicine_stock.html', {
        'batches': batches,
        'all_medicines': all_medicines,
        'categories': categories,
        'search_query': search_query,
        'category_filter': category_filter,
        'stock_filter': stock_filter,
    })


@login_required
def edit_batch(request, batch_id):
    """Edit batch by adding new medicines to it."""
    # Get all batch items with this batch_id
    batch_items = MedicineBatch.objects.filter(batch_id=batch_id)

    if not batch_items.exists():
        messages.error(request, f"Batch {batch_id} not found.")
        return redirect('medicine_stock')

    # Get batch info from first item
    first_item = batch_items.first()
    expiry_date = first_item.expiry_date
    date_received = first_item.date_received

    # Get unique categories from database
    categories = Medicine.objects.values_list('category', flat=True).distinct().order_by('category')
    categories = [cat for cat in categories if cat]

    if request.method == 'POST':
        medicine_names = request.POST.getlist('medicine_name[]')
        brands = request.POST.getlist('brand[]')
        categories_list = request.POST.getlist('category[]')
        descriptions = request.POST.getlist('description[]')
        quantities = request.POST.getlist('quantity[]')

        added_count = 0

        with transaction.atomic():
            for i in range(len(medicine_names)):
                medicine_name = medicine_names[i].strip()
                brand = brands[i].strip() if brands[i] else ''
                category = categories_list[i].strip() if categories_list[i] else ''
                description = descriptions[i].strip() if descriptions[i] else ''

                try:
                    quantity = int(quantities[i])
                except (ValueError, IndexError):
                    quantity = 0

                if not medicine_name or quantity <= 0:
                    continue

                try:
                    # Check if medicine already exists (case-insensitive)
                    medicine = Medicine.objects.filter(name__iexact=medicine_name).first()

                    if medicine:
                        # Medicine exists - update fields if provided
                        if brand:
                            medicine.brand = brand
                        if category:
                            medicine.category = category
                        if description:
                            medicine.description = description
                        medicine.save()
                    else:
                        # Medicine doesn't exist - create new one
                        medicine = Medicine.objects.create(
                            name=medicine_name,
                            brand=brand,
                            category=category,
                            description=description
                        )

                    # Check if this medicine already exists in this batch
                    existing_batch = MedicineBatch.objects.filter(
                        batch_id=batch_id,
                        medicine=medicine
                    ).first()

                    if existing_batch:
                        messages.warning(request, f"{medicine_name} already exists in batch {batch_id}. Skipped.")
                        continue

                    # Create new batch entry
                    MedicineBatch.objects.create(
                        medicine=medicine,
                        batch_id=batch_id,
                        quantity_received=quantity,
                        quantity_available=quantity,
                        quantity_dispensed=0,
                        expiry_date=expiry_date,
                        date_received=date_received
                    )

                    added_count += 1

                except Exception as e:
                    messages.error(request, f"Error adding {medicine_name}: {str(e)}")
                    continue

        if added_count > 0:
            messages.success(request, f"✅ Added {added_count} medicine(s) to batch {batch_id}.")

        return redirect('medicine_stock')

    context = {
        'batch_id': batch_id,
        'batch_items': batch_items,
        'expiry_date': expiry_date,
        'date_received': date_received,
        'categories': categories,
    }

    return render(request, 'edit_batch.html', context)

# -------------------------------------------------------------------
# Medicine Records Page
# -------------------------------------------------------------------
@login_required
def medicine_records(request):
    return render(request, 'medicine_records.html')


# -------------------------------------------------------------------
# Edit Medicine
# -------------------------------------------------------------------
@login_required
def edit_medicine(request, id):
    """Edit medicine details."""
    medicine = get_object_or_404(Medicine, id=id)

    if request.method == 'POST':
        medicine.name = request.POST.get('name')
        medicine.brand = request.POST.get('brand')
        medicine.category = request.POST.get('category')
        medicine.description = request.POST.get('description')
        medicine.save()
        messages.success(request, f"✅ {medicine.name} updated successfully!")
        return redirect('medicine_stock')

    return render(request, 'edit_medicine.html', {'medicine': medicine})


# -------------------------------------------------------------------
# Delete Medicine
# -------------------------------------------------------------------
@login_required
def delete_medicine(request, id):
    """Delete medicine batch."""
    if request.method in ["POST", "GET"]:
        try:
            batch = MedicineBatch.objects.get(id=id)
            batch_id = batch.batch_id
            medicine_name = batch.medicine.name
            batch.delete()
            messages.success(request, f"🗑️ {medicine_name} from {batch_id} deleted successfully!")
        except MedicineBatch.DoesNotExist:
            messages.error(request, "⚠️ Batch not found.")
        except Exception as e:
            messages.error(request, f"⚠️ Error deleting batch: {e}")

    return redirect("medicine_stock")


# 🟢 Add medicine to order
@login_required
def add_to_order(request, medicine_id):
    medicine = get_object_or_404(Medicine, id=medicine_id)

    if request.method == "POST":
        quantity = int(request.POST.get("quantity", 1))
        special_request = request.POST.get("special_request", "")

        # ✅ USE total_stock PROPERTY INSTEAD OF stock_quantity
        if quantity > medicine.total_stock:
            messages.warning(request, f"⚠️ Only {medicine.total_stock} available in stock.")
            return redirect("medicine_info", medicine_id=medicine.id)

        # Get or create pending order (cart)
        order, created = Order.objects.get_or_create(
            user=request.user,
            status="Pending",
            defaults={"created_at": timezone.now()}
        )

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

        messages.success(request, f"✅ Added {quantity} × {medicine.name} to your order.")

        # 🔧 Redirect to order_list (Current Orders) to review cart
        return redirect("order_list")

    # GET request - just show the medicine info page
    return redirect("medicine_info", medicine_id=medicine.id)

# -------------------------------------------------------------------
# Medicine List (Public Browse)
# -------------------------------------------------------------------
@login_required
def medicine_list(request):
    """Display list of medicines with search and filter capabilities."""
    # Get all medicines
    medicines = Medicine.objects.all()

    # Get unique categories for filter dropdown
    categories = Medicine.objects.values_list('category', flat=True).distinct().order_by('category')
    categories = [cat for cat in categories if cat]

    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        medicines = medicines.filter(
            name__icontains=search_query
        ) | medicines.filter(
            brand__icontains=search_query
        )

    # Category filter
    category_filter = request.GET.get('category', '')
    if category_filter:
        medicines = medicines.filter(category=category_filter)

    # Stock filter
    stock_filter = request.GET.get('stock', '')
    if stock_filter:
        if stock_filter == 'in-stock':
            # Filter medicines with total_stock > 10
            medicines = [m for m in medicines if m.total_stock > 10]
        elif stock_filter == 'low-stock':
            # Filter medicines with 1 <= total_stock <= 10
            medicines = [m for m in medicines if 0 < m.total_stock <= 10]
        elif stock_filter == 'out-of-stock':
            # Filter medicines with total_stock == 0
            medicines = [m for m in medicines if m.total_stock == 0]

    # ✅ Add batch information for each medicine
    for medicine in medicines:
        # Get all batches for this medicine with available quantity
        medicine.batch_list = MedicineBatch.objects.filter(
            medicine=medicine,
            quantity_available__gt=0
        ).order_by('expiry_date', 'batch_id').values_list('batch_id', flat=True).distinct()

    context = {
        'medicines': medicines,
        'categories': categories,
        'search_query': search_query,
        'category_filter': category_filter,
        'stock_filter': stock_filter,
    }

    return render(request, 'medicine_list.html', context)


# -------------------------------------------------------------------
# Medicine Info Page
# -------------------------------------------------------------------
def medicine_info(request, medicine_id):
    """Medicine details page."""
    medicine = get_object_or_404(Medicine, id=medicine_id)
    return render(request, 'medicine_info.html', {'medicine': medicine})