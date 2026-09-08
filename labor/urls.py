from django.urls import path
from . import views

urlpatterns = [
    # Labor Entries (scoped to project)
    path('projects/<int:project_pk>/labor/create/', views.LaborCreateView.as_view(), name='labor_create'),
    path('projects/<int:project_pk>/labor/summary/', views.LaborSummaryView.as_view(), name='labor_summary'),

    # App specific URLs
    path('labor/<int:pk>/update/', views.LaborUpdateView.as_view(), name='labor_update'),
    path('labor/<int:pk>/delete/', views.LaborDeleteView.as_view(), name='labor_delete'),
]

