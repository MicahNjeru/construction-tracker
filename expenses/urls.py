from django.urls import path
from . import views

urlpatterns = [
    # Expense Entry URLs
    path('project/<int:project_pk>/expenses/', views.ExpenseListView.as_view(), name='expense_list'),
    path('project/<int:project_pk>/expenses/create/', views.ExpenseCreateView.as_view(), name='expense_create'),
    path('expenses/<int:pk>/update/', views.ExpenseUpdateView.as_view(), name='expense_update'),
    path('expenses/<int:pk>/delete/', views.ExpenseDeleteView.as_view(), name='expense_delete'),
    path('expenses/<int:pk>/', views.ExpenseDetailView.as_view(), name='expense_detail'),

    # Receipt URLs
    path('expenses/<int:expense_pk>/upload-receipt/', views.ExpenseReceiptUploadView.as_view(), name='expense_receipt_upload'),
    path('receipts/<int:pk>/delete/', views.ExpenseReceiptDeleteView.as_view(), name='expense_receipt_delete'),

    # API URLs
    path('api/expense-categories/', views.ExpenseCategoriesAPIView.as_view(), name='expense_api_categories'),
    path('api/project/<int:project_pk>/expense-summary/', views.ExpenseSummaryAPIView.as_view(), name='expense_api_summary'),
]

