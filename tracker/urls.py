from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Projects
    path('projects/', views.project_list, name='project_list'),
    path('projects/create/', views.project_create, name='project_create'),
    path('projects/<int:pk>/', views.project_detail, name='project_detail'),
    path('projects/<int:pk>/update/', views.project_update, name='project_update'),
    path('projects/<int:pk>/delete/', views.project_delete, name='project_delete'),
    
    # Export
    path('projects/<int:pk>/export/excel/', views.export_project_excel, name='export_project_excel'),
    path('projects/<int:pk>/export/pdf/', views.export_project_pdf, name='export_project_pdf'),
    
    # Materials
    path('projects/<int:project_pk>/materials/create/', views.material_create, name='material_create'),
    path('materials/<int:pk>/update/', views.material_update, name='material_update'),
    path('materials/<int:pk>/delete/', views.material_delete, name='material_delete'),
    
    # Receipts
    path('materials/<int:material_pk>/receipts/', views.receipt_gallery, name='receipt_gallery'),
    path('materials/<int:material_pk>/receipt/upload/', views.receipt_upload, name='receipt_upload'),
    path('receipts/<int:pk>/view/', views.receipt_view, name='receipt_view'),
    path('receipts/<int:pk>/download/', views.receipt_download, name='receipt_download'),
    path('receipts/<int:pk>/delete/', views.receipt_delete, name='receipt_delete'),
    path('receipts/<int:pk>/set-primary/', views.receipt_set_primary, name='receipt_set_primary'),
]