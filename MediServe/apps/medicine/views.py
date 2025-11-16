from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Medicine
from .forms import MedicineForm


# -------------------------------------------------------------------
# Medicine History Page
# -------------------------------------------------------------------
@login_required
def medicine_history(request):
    return render(request, 'medicine_history.html')


# -------------------------------------------------------------------
# Admin: Medicine Stock (Main CRUD Page)
# -------------------------------------------------------------------
@login_required
def medicine_stock(request):
    """Medicine stock management (admin view)."""
    medicines = Medicine.objects.all().order_by('-id')  # Newest first

    # Search functionality
    search_query = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    stock_filter = request.GET.get('stock', '')

    if search_query:
        medicines = medicines.filter(
            Q(name__icontains=search_query) |
            Q(brand__icontains=search_query) |
            Q(category__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    if category_filter:
        medicines = medicines.filter(category__iexact=category_filter)

    if stock_filter:
        if stock_filter == 'low':
            medicines = medicines.filter(stock_quantity__lte=10)
        elif stock_filter == 'medium':
            medicines = medicines.filter(stock_quantity__gt=10, stock_quantity__lte=50)
        elif stock_filter == 'high':
            medicines = medicines.filter(stock_quantity__gt=50)

    # Get unique categories for filter dropdown
    categories = Medicine.objects.values_list('category', flat=True).distinct()

    if request.method == 'POST':
        form = MedicineForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Medicine added successfully!')
            return redirect('medicine_stock')
        else:
            messages.error(request, '⚠️ Please correct the errors below.')
    else:
        form = MedicineForm()

    return render(request, 'medicine_stock.html', {
        'medicines': medicines,
        'form': form,
        'categories': categories,
        'search_query': search_query,
        'category_filter': category_filter,
        'stock_filter': stock_filter,
    })


# -------------------------------------------------------------------
# Medicine Records Page (if needed separately)
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
        form = MedicineForm(request.POST, instance=medicine)
        if form.is_valid():
            form.save()
            messages.success(request, f"✅ {medicine.name} updated successfully!")
            return redirect('medicine_stock')
        else:
            messages.error(request, "⚠️ Please correct the errors below.")
    else:
        form = MedicineForm(instance=medicine)

    return render(request, 'edit_medicine.html', {
        'form': form,
        'medicine': medicine,
    })


# -------------------------------------------------------------------
# Delete Medicine (Instant Delete, No Confirmation Page)
# -------------------------------------------------------------------
@login_required
def delete_medicine(request, id):
    """Delete medicine directly from local DB."""
    if request.method in ["POST", "GET"]:
        try:
            medicine = Medicine.objects.get(id=id)
            medicine_name = medicine.name
            medicine.delete()
            messages.success(request, f"🗑️ {medicine_name} deleted successfully!")
        except Medicine.DoesNotExist:
            messages.error(request, "⚠️ Medicine not found.")
        except Exception as e:
            messages.error(request, f"⚠️ Error deleting medicine: {e}")

    return redirect("medicine_stock")


#Medicine info list
def medicine_list(request):
    """Public Browse Medicines page with filtering."""
    medicines = Medicine.objects.all().order_by('name')

    # Get filter parameters
    search_query = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    stock_filter = request.GET.get('stock', '')

    # Apply search filter
    if search_query:
        medicines = medicines.filter(
            Q(name__icontains=search_query) |
            Q(brand__icontains=search_query) |
            Q(category__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Apply category filter
    if category_filter:
        medicines = medicines.filter(category__iexact=category_filter)

    # Apply stock filter
    if stock_filter:
        if stock_filter == 'in-stock':
            medicines = medicines.filter(stock_quantity__gt=10)
        elif stock_filter == 'low-stock':
            medicines = medicines.filter(stock_quantity__gt=0, stock_quantity__lte=10)
        elif stock_filter == 'out-of-stock':
            medicines = medicines.filter(stock_quantity=0)

    # Get unique categories for filter options
    categories = Medicine.objects.values_list('category', flat=True).distinct().order_by('category')
    categories = [cat for cat in categories if cat]  # Remove None values

    return render(request, 'medicine_list.html', {
        'medicines': medicines,
        'categories': categories,
        'search_query': search_query,
        'category_filter': category_filter,
        'stock_filter': stock_filter,
    })

# -------------------------------------------------------------------
# Medicine Info Page
# -------------------------------------------------------------------
def medicine_info(request, medicine_id):
    """Medicine details page."""
    medicine = get_object_or_404(Medicine, id=medicine_id)
    return render(request, 'medicine_info.html', {'medicine': medicine})