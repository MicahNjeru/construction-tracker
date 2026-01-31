from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # User Profile
    path('profile/', views.user_profile, name='user_profile'),
    
    # Projects
    path('projects/', views.project_list, name='project_list'),
    path('projects/create/', views.project_create, name='project_create'),
    path('projects/<int:pk>/', views.project_detail, name='project_detail'),
    path('projects/<int:pk>/update/', views.project_update, name='project_update'),
    path('projects/<int:pk>/delete/', views.project_delete, name='project_delete'),

    # Project Photos
    path('projects/<int:project_pk>/photos/', views.project_photos, name='project_photos'),
    path('projects/<int:project_pk>/photos/upload/', views.photo_upload, name='photo_upload'),
    path('photos/<int:pk>/delete/', views.photo_delete, name='photo_delete'),
    
    # Export
    path('projects/<int:pk>/export/excel/', views.export_project_excel, name='export_project_excel'),
    path('projects/<int:pk>/export/pdf/', views.export_project_pdf, name='export_project_pdf'),
    
    # Materials
    path('projects/<int:project_pk>/materials/create/', views.material_create, name='material_create'),
    path('materials/<int:pk>/update/', views.material_update, name='material_update'),
    path('materials/<int:pk>/delete/', views.material_delete, name='material_delete'),
    path('materials/<int:pk>/usage/', views.update_material_usage, name='update_material_usage'),
    path('materials/<int:pk>/quick-usage/', views.quick_update_usage, name='quick_update_usage'),
    
    # Receipts
    path('materials/<int:material_pk>/receipts/', views.receipt_gallery, name='receipt_gallery'),
    path('materials/<int:material_pk>/receipt/upload/', views.receipt_upload, name='receipt_upload'),
    path('receipts/<int:pk>/view/', views.receipt_view, name='receipt_view'),
    path('receipts/<int:pk>/download/', views.receipt_download, name='receipt_download'),
    path('receipts/<int:pk>/delete/', views.receipt_delete, name='receipt_delete'),
    path('receipts/<int:pk>/set-primary/', views.receipt_set_primary, name='receipt_set_primary'),

    # Templates
    path('templates/', views.template_list, name='template_list'),
    path('templates/create/', views.template_create, name='template_create'),
    path('templates/<int:pk>/', views.template_detail, name='template_detail'),
    path('templates/<int:pk>/update/', views.template_update, name='template_update'),
    path('templates/<int:pk>/delete/', views.template_delete, name='template_delete'),
    path('templates/<int:template_pk>/add-material/', views.template_add_material, name='template_add_material'),
    path('templates/<int:pk>/materials/<int:material_pk>/update/', views.template_material_update, name='template_material_update'),
    path('templates/<int:pk>/materials/<int:material_pk>/delete/', views.template_material_delete, name='template_material_delete'),
    path('projects/create-from-template/', views.create_project_from_template, name='create_from_template'),
    
    # Activity Timeline
    path('projects/<int:pk>/timeline/', views.project_timeline, name='project_timeline'),
    
    # Budget Alerts
    path('alerts/', views.budget_alerts, name='budget_alerts'),
    path('alerts/<int:pk>/mark-read/', views.mark_alert_read, name='mark_alert_read'),
]