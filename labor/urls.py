# labor/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Labor Entries (scoped to project)
    path('projects/<int:project_pk>/labor/create/', views.labor_create, name='labor_create'),
    path('projects/<int:project_pk>/labor/summary/', views.labor_summary, name='labor_summary'),

    # App specific URLs
    path('labor/<int:pk>/update/', views.labor_update, name='labor_update'),
    path('labor/<int:pk>/delete/', views.labor_delete, name='labor_delete'),
]