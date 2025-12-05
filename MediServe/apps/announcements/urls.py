from django.urls import path
from . import views

urlpatterns = [
    path('', views.announcements_view, name='announcements'),
    path('edit/<int:post_id>/', views.edit_post, name='edit_post'),
    path('view-announcements/', views.view_announcements, name='view_announcements'),
    path('add/', views.add_post, name='add_post'),
    path('admin-menu/', views.admin_menu, name='admin_menu'),

    # ARCHIVE SYSTEM
    path('archived/', views.archived_announcements_view, name='archived_announcements'),
    path('archive/<int:post_id>/', views.archive_post, name='archive_post'),
    path('restore/<int:post_id>/', views.restore_post, name='restore_post'),
]
