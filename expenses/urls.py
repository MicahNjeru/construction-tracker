from django.urls import path
from . import views

urlpatterns = [
    # Expense Entry URLs
    path('project/<int:project_pk>/expenses/', views.expense_list, name='expense_list'),
    path('project/<int:project_pk>/expenses/create/', views.expense_create, name='expense_create'),
    path('expenses/<int:pk>/update/', views.expense_update, name='expense_update'),
    path('expenses/<int:pk>/delete/', views.expense_delete, name='expense_delete'),
    path('expenses/<int:pk>/', views.expense_detail, name='expense_detail'),
    
    # Receipt URLs
    path('expenses/<int:expense_pk>/upload-receipt/', views.expense_receipt_upload, name='expense_receipt_upload'),
    path('receipts/<int:pk>/delete/', views.expense_receipt_delete, name='expense_receipt_delete'),
    
    # API URLs
    path('api/expense-categories/', views.expense_api_categories, name='expense_api_categories'),
    path('api/project/<int:project_pk>/expense-summary/', views.expense_api_summary, name='expense_api_summary'),
]

