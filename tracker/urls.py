from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),

    # User Profile
    path('profile/', views.UserProfileView.as_view(), name='user_profile'),

    # Projects
    path('projects/', views.ProjectListView.as_view(), name='project_list'),
    path('projects/create/', views.ProjectCreateView.as_view(), name='project_create'),
    path('projects/<int:pk>/', views.ProjectDetailView.as_view(), name='project_detail'),
    path('projects/<int:pk>/update/', views.ProjectUpdateView.as_view(), name='project_update'),
    path('projects/<int:pk>/delete/', views.ProjectDeleteView.as_view(), name='project_delete'),

    # Project Photos
    path('projects/<int:project_pk>/photos/', views.ProjectPhotosView.as_view(), name='project_photos'),
    path('projects/<int:project_pk>/photos/upload/', views.PhotoUploadView.as_view(), name='photo_upload'),
    path('photos/<int:pk>/delete/', views.PhotoDeleteView.as_view(), name='photo_delete'),

    # Export
    path('projects/<int:pk>/export/excel/', views.ExportProjectExcelView.as_view(), name='export_project_excel'),
    path('projects/<int:pk>/export/pdf/', views.ExportProjectPDFView.as_view(), name='export_project_pdf'),

    # Materials
    path('projects/<int:project_pk>/materials/create/', views.MaterialCreateView.as_view(), name='material_create'),
    path('materials/<int:pk>/update/', views.MaterialUpdateView.as_view(), name='material_update'),
    path('materials/<int:pk>/delete/', views.MaterialDeleteView.as_view(), name='material_delete'),
    path('materials/<int:pk>/usage/', views.MaterialUsageUpdateView.as_view(), name='update_material_usage'),
    path('materials/<int:pk>/quick-usage/', views.QuickUsageUpdateView.as_view(), name='quick_update_usage'),

    # Receipts
    path('materials/<int:material_pk>/receipts/', views.ReceiptGalleryView.as_view(), name='receipt_gallery'),
    path('materials/<int:material_pk>/receipt/upload/', views.ReceiptUploadView.as_view(), name='receipt_upload'),
    path('receipts/<int:pk>/view/', views.ReceiptViewView.as_view(), name='receipt_view'),
    path('receipts/<int:pk>/download/', views.ReceiptDownloadView.as_view(), name='receipt_download'),
    path('receipts/<int:pk>/delete/', views.ReceiptDeleteView.as_view(), name='receipt_delete'),
    path('receipts/<int:pk>/set-primary/', views.ReceiptSetPrimaryView.as_view(), name='receipt_set_primary'),

    # Templates
    path('templates/', views.TemplateListView.as_view(), name='template_list'),
    path('templates/create/', views.TemplateCreateView.as_view(), name='template_create'),
    path('templates/<int:pk>/', views.TemplateDetailView.as_view(), name='template_detail'),
    path('templates/<int:pk>/update/', views.TemplateUpdateView.as_view(), name='template_update'),
    path('templates/<int:pk>/delete/', views.TemplateDeleteView.as_view(), name='template_delete'),
    path('templates/<int:template_pk>/add-material/', views.TemplateAddMaterialView.as_view(), name='template_add_material'),
    path('templates/<int:pk>/materials/<int:material_pk>/update/', views.TemplateMaterialUpdateView.as_view(), name='template_material_update'),
    path('templates/<int:pk>/materials/<int:material_pk>/delete/', views.TemplateMaterialDeleteView.as_view(), name='template_material_delete'),
    path('projects/create-from-template/', views.CreateProjectFromTemplateView.as_view(), name='create_from_template'),

    # Activity Timeline
    path('projects/<int:pk>/timeline/', views.ProjectTimelineView.as_view(), name='project_timeline'),

    # Budget Alerts
    path('alerts/', views.BudgetAlertsView.as_view(), name='budget_alerts'),
    path('alerts/<int:pk>/mark-read/', views.MarkAlertReadView.as_view(), name='mark_alert_read'),
]

