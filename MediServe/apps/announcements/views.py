from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Announcement


# Helper: check if admin
def is_admin_user(user):
    return user.is_staff or user.email == "admin123@gmail.com"


# -----------------------------------------------------------
# ADMIN — Active Announcements
# -----------------------------------------------------------
@login_required
def announcements_view(request):
    if not is_admin_user(request.user):
        messages.error(request, "Access denied. Admins only.")
        return redirect("main_menu")

    # Auto-archive posts older than 30 days
    Announcement.auto_archive_old_announcements()

    # Add new announcement
    if request.method == "POST":
        title = request.POST.get("title")
        content = request.POST.get("content")

        if not title or not content:
            messages.error(request, "Please fill in all fields.")
            return redirect("announcements")

        Announcement.objects.create(
            title=title,
            content=content,
            status="active"
        )

        messages.success(request, "Announcement posted successfully!")
        return redirect("announcements")

    announcements = Announcement.objects.filter(status="active").order_by("-date_posted")

    return render(request, "announcements.html", {
        "announcements": announcements,
        "is_admin": True,
    })


# -----------------------------------------------------------
# ADMIN — Archived Announcements
# -----------------------------------------------------------
@login_required
def archived_announcements_view(request):
    if not is_admin_user(request.user):
        messages.error(request, "Access denied.")
        return redirect("announcements")

    archived_list = Announcement.objects.filter(status="archived").order_by("-archived_at")

    return render(request, "admin_archived_announcements.html", {
        "announcements": archived_list,
        "is_admin": True
    })


# -----------------------------------------------------------
# ARCHIVE a post (no delete)
# -----------------------------------------------------------
@login_required
def archive_post(request, post_id):
    if not is_admin_user(request.user):
        messages.error(request, "Unauthorized access.")
        return redirect("announcements")

    announcement = get_object_or_404(Announcement, id=post_id)

    announcement.status = "archived"
    announcement.archived_at = timezone.now()
    announcement.save()

    messages.success(request, "Announcement moved to Archive.")
    return redirect("announcements")


# -----------------------------------------------------------
# RESTORE from archive
# -----------------------------------------------------------
@login_required
def restore_post(request, post_id):
    if not is_admin_user(request.user):
        messages.error(request, "Unauthorized access.")
        return redirect("archived_announcements")

    announcement = get_object_or_404(Announcement, id=post_id)

    announcement.status = "active"
    announcement.archived_at = None
    announcement.save()

    messages.success(request, "Announcement restored.")
    return redirect("archived_announcements")


# -----------------------------------------------------------
# EDIT Announcement
# -----------------------------------------------------------
@login_required
def edit_post(request, post_id):
    if not is_admin_user(request.user):
        messages.error(request, "Unauthorized access.")
        return redirect("announcements")

    announcement = get_object_or_404(Announcement, id=post_id)

    if request.method == "POST":
        title = request.POST.get("title")
        content = request.POST.get("content")

        if not title or not content:
            messages.error(request, "Please fill in all fields.")
            return redirect("announcements")

        announcement.title = title
        announcement.content = content
        announcement.save()

        messages.success(request, "Announcement updated successfully.")
        return redirect("announcements")

    return render(request, "edit_announcement.html", {
        "announcement": announcement
    })


# -----------------------------------------------------------
# User View (no admin tools)
# -----------------------------------------------------------
@login_required
def view_announcements(request):
    announcements = Announcement.objects.filter(status="active").order_by("-date_posted")
    return render(request, "view_announcements.html", {
        "announcements": announcements
    })


# -----------------------------------------------------------
# Simple Add Page (optional)
# -----------------------------------------------------------
@login_required
def add_post(request):
    if not is_admin_user(request.user):
        messages.error(request, "Unauthorized access.")
        return redirect("main_menu")

    if request.method == "POST":
        title = request.POST.get("title")
        content = request.POST.get("content")

        if not title or not content:
            messages.error(request, "Please fill in all fields.")
            return redirect("announcements")

        Announcement.objects.create(title=title, content=content)
        messages.success(request, "Announcement posted successfully!")
        return redirect("announcements")

    return render(request, "add_post.html")


# -----------------------------------------------------------
# Admin Menu — Show Latest Announcement
# -----------------------------------------------------------
@login_required
def admin_menu(request):
    if not is_admin_user(request.user):
        messages.error(request, "Access denied.")
        return redirect("main_menu")

    latest = Announcement.objects.filter(status="active").order_by("-date_posted").first()
    recent_announcement = (
        f"{latest.title} - {latest.content}" if latest
        else "No announcements posted yet."
    )

    return render(request, "admin_menu.html", {
        "recent_announcement": recent_announcement,
        "is_admin": True
    })
