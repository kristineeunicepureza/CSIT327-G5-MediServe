from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required

from .forms import SignupForm, LoginForm
from .models import Account
from apps.announcements.models import Announcement
from apps.medicine.models import Medicine
from apps.orders.models import Order


def home_redirect(request):
    return redirect('login')


def signup_view(request):
    if request.method == 'POST':
        # include FILES for uploaded images
        form = SignupForm(request.POST, request.FILES)

        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        # password check
        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'signup.html', {'form': form})

        # existing email check
        if Account.objects.filter(email=email).exists():
            messages.error(request, 'An account with this email already exists.')
            return render(request, 'signup.html', {'form': form})

        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])

            # Optional file fields (use request.FILES safely)
            user.barangay_id = request.FILES.get('barangay_id')
            user.pwd_id = request.FILES.get('pwd_id')
            user.senior_citizen_id = request.FILES.get('senior_id')

            user.save()
            messages.success(request, 'Signup successful! Please log in.')
            return redirect('login')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = SignupForm()

    return render(request, 'signup.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        email = request.POST.get('username')
        password = request.POST.get('password')

        user_exists = Account.objects.filter(email=email).exists()

        if not user_exists:
            messages.error(request, 'No account found with this email. Please sign up first.')
        else:
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                if user.is_staff or user.is_superuser:
                    return redirect('admin_menu')
                else:
                    return redirect('main_menu')
            else:
                messages.error(request, 'Invalid email or password.')
    else:
        form = LoginForm()

    return render(request, 'login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.success(request, 'Logged out successfully.')
    return redirect('login')


@login_required
def admin_menu_view(request):
    return render(request, 'admin_menu.html')


@login_required
def main_menu_view(request):
    """Main menu view that shows the most recent announcement (Django ORM only)."""
    latest_announcement = Announcement.objects.order_by('-date_posted').first()

    return render(request, 'main_menu.html', {
        'latest_announcement': latest_announcement
    })


@login_required
def profile_view(request):
    """Profile view for regular users"""
    profile = request.user
    if request.method == 'POST':
        # Update logic if you allow saving form data
        profile.first_name = request.POST.get('first_name')
        profile.last_name = request.POST.get('last_name')
        profile.middle_name = request.POST.get('middle_name', '')
        profile.date_of_birth = request.POST.get('date_of_birth')
        profile.gender = request.POST.get('sex')
        profile.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('profile_view')

    return render(request, 'profile_view.html', {'profile': profile})


@login_required
def admin_profile_view(request):
    """Profile view specifically for administrators"""
    # Check if user is admin
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'Access denied. Admins only.')
        return redirect('main_menu')

    # Get statistics for the profile page
    total_orders = Order.objects.count()
    total_medicines = Medicine.objects.count()
    total_users = Account.objects.filter(is_staff=False).count()
    pending_orders = Order.objects.filter(status='Pending').count()

    if request.method == 'POST':
        # Update admin profile
        user = request.user
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.middle_name = request.POST.get('middle_name', '')
        user.date_of_birth = request.POST.get('date_of_birth')
        user.gender = request.POST.get('gender')
        user.save()
        messages.success(request, 'Admin profile updated successfully!')
        return redirect('admin_profile')

    context = {
        'user': request.user,
        'total_orders': total_orders,
        'total_medicines': total_medicines,
        'total_users': total_users,
        'pending_orders': pending_orders,
    }

    return render(request, 'admin_profile.html', context)


@login_required
def settings_page(request):
    return render(request, 'settings.html')


@login_required
def feedback_page(request):
    return render(request, 'feedback.html')