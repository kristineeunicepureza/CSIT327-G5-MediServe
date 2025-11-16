from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from utils.supabase_client import supabase
from datetime import datetime
from django.utils import timezone
from .models import Announcement


# ------------------------------
# ADMIN: Manage Announcements
# ------------------------------

@login_required
def announcements_view(request):
    """Admin can view, add, edit, and delete announcements."""
    # ✅ Check admin access
    is_admin = request.user.is_staff or request.user.email == "admin123@gmail.com"

    if not is_admin:
        messages.error(request, "Access denied. Admins only.")
        return redirect('main_menu')

    # ✅ Add new announcement
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')

        if not title or not content:
            messages.error(request, "Please fill in all fields.")
            return redirect('announcements')

        # Use Django ORM instead of Supabase for consistency
        Announcement.objects.create(
            title=title,
            content=content
            # date_posted will be set automatically by auto_now_add=True
        )

        messages.success(request, "Announcement posted successfully!")
        return redirect('announcements')

    # ✅ Fetch all announcements using Django ORM
    announcements = Announcement.objects.all().order_by('-date_posted')

    return render(request, 'announcements.html', {
        'announcements': announcements,
        'is_admin': is_admin
    })


# ------------------------------
# ADMIN: Edit an Announcement
# ------------------------------

@login_required
def edit_post(request, post_id):
    """Admin edits an existing announcement."""
    if not request.user.is_staff and request.user.email != "admin123@gmail.com":
        messages.error(request, "Unauthorized access.")
        return redirect("announcements")

    try:
        announcement = Announcement.objects.get(id=post_id)
    except Announcement.DoesNotExist:
        messages.error(request, "Announcement not found.")
        return redirect("announcements")

    if request.method == "POST":
        title = request.POST.get("title")
        content = request.POST.get("content")

        if not title or not content:
            messages.error(request, "Title and content are required.")
            return redirect("announcements")

        # Update using Django ORM
        announcement.title = title
        announcement.content = content
        announcement.save()

        messages.success(request, "Announcement updated successfully.")
        return redirect("announcements")

    return render(request, "edit_announcement.html", {"announcement": announcement})


# ------------------------------
# ADMIN: Delete an Announcement
# ------------------------------

@login_required
def delete_post(request, post_id):
    """Admin deletes an announcement."""
    if not request.user.is_staff and request.user.email != "admin123@gmail.com":
        messages.error(request, "Unauthorized access.")
        return redirect("announcements")

    try:
        announcement = Announcement.objects.get(id=post_id)
        announcement.delete()
        messages.success(request, "Announcement deleted successfully.")
    except Announcement.DoesNotExist:
        messages.error(request, "Announcement not found.")

    return redirect("announcements")


# ------------------------------
# USER: View Announcements
# ------------------------------

@login_required
def view_announcements(request):
    """Users view all posted announcements."""
    announcements = Announcement.objects.all().order_by('-date_posted')
    return render(request, "view_announcements.html", {"announcements": announcements})


# ------------------------------
# ADMIN: Add Post (Alternative method)
# ------------------------------

@login_required
def add_post(request):
    """Alternative add post view if using separate page."""
    if not request.user.is_staff and request.user.email != "admin123@gmail.com":
        messages.error(request, "Unauthorized access.")
        return redirect("announcements")

    if request.method == "POST":
        title = request.POST.get("title")
        content = request.POST.get("content")

        if not title or not content:
            messages.error(request, "Please fill in all fields.")
            return redirect('announcements')

        # Save announcement using Django ORM
        Announcement.objects.create(title=title, content=content)
        messages.success(request, "Announcement posted successfully!")
        return redirect('announcements')

    return render(request, 'add_post.html')


# ------------------------------
# ADMIN: Admin Menu Dashboard
# ------------------------------

@login_required
def admin_menu(request):
    """Admin dashboard view with latest announcement."""
    # Check admin access
    is_admin = request.user.is_staff or request.user.email == "admin123@gmail.com"

    if not is_admin:
        messages.error(request, "Access denied. Admins only.")
        return redirect('main_menu')

    # Fetch the most recent announcement
    try:
        latest = Announcement.objects.order_by('-date_posted').first()
        if latest:
            recent_announcement = f"{latest.title} - {latest.content}"
        else:
            recent_announcement = "No announcements posted yet. Click 'Announcements' to add one."
    except Exception as e:
        recent_announcement = "Unable to load announcements."

    return render(request, 'admin_menu.html', {
        'recent_announcement': recent_announcement,
        'is_admin': is_admin
    })