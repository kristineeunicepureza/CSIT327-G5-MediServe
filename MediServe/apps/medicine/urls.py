from django.urls import path
from . import views

urlpatterns = [
    # User-facing pages (browse medicines - only active)
    path('', views.medicine_list, name='medicine_list'),
    path('<int:medicine_id>/', views.medicine_info, name='medicine_info'),
    path('browse-medicines/', views.medicine_list, name='medicine_list'),

    # Medicine history and records
    path('history/', views.medicine_history, name='medicine_history'),
    path('records/', views.medicine_records, name='medicine_records'),

    # Admin stock management
    path('admin/medicine-stock/', views.medicine_stock, name='medicine_stock'),

    # Archive management (admin only) - UPDATED
    path('admin/archived/', views.archived_medicines, name='archived_medicines'),
    path('admin/archive/<int:batch_id>/', views.archive_batch, name='archive_batch'),
    path('admin/archived/delete/<int:batch_id>/', views.delete_archived_batch, name='delete_archived_batch'),  # NEW
    # path('admin/restore/<int:batch_id>/', views.restore_batch, name='restore_batch'),  # COMMENTED OUT

    # Edit medicine/batch (admin only)
    path('edit/<int:id>/', views.edit_medicine, name='edit_medicine'),
    path('edit-batch/<str:batch_id>/', views.edit_batch, name='edit_batch'),

    # DEPRECATED: Delete (kept for backward compatibility)
    path('delete/<int:id>/', views.delete_medicine, name='delete_medicine'),

    # Distribution history (admin only)
    path('distribution-history/', views.medicine_distribution_history, name='medicine_distribution_history'),
]