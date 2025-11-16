from django.urls import path
from . import views

urlpatterns = [
    path('', views.announcements_view, name='announcements'),  # admin can add/edit/delete
    path('edit/<int:post_id>/', views.edit_post, name='edit_post'),
    path('delete/<int:post_id>/', views.delete_post, name='delete_post'),
    path('view-announcements/', views.view_announcements, name='view_announcements'),  # users can only view
    path('add/', views.add_post, name='add_post'),
    path('admin-menu/', views.admin_menu, name='admin_menu'),
]
