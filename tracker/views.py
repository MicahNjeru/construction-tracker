from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count
from .models import Project, MaterialEntry, Receipt, MaterialUnit
from .forms import ProjectForm, MaterialEntryForm, ReceiptUploadForm
from django.http import FileResponse, Http404
import os

# Create your views here.


@login_required
def project_list(request):
    """Display list of all projects."""
    projects = Project.objects.filter(created_by=request.user)
    
    # Calculate summary statistics
    total_projects = projects.count()
    active_projects = projects.filter(status='in_progress').count()
    completed_projects = projects.filter(status='completed').count()
    total_budget = projects.aggregate(Sum('budget'))['budget__sum'] or 0
    
    context = {
        'projects': projects,
        'total_projects': total_projects,
        'active_projects': active_projects,
        'completed_projects': completed_projects,
        'total_budget': total_budget,
    }
    return render(request, 'tracker/project_list.html', context)


@login_required
def project_detail(request, pk):
    """Display project details and materials."""
    project = get_object_or_404(Project, pk=pk)
    materials = project.material_entries.all()
    
    # Material breakdown by type
    material_breakdown = materials.values('material_type').annotate(
        total_cost=Sum('cost'),
        count=Count('id')
    ).order_by('-total_cost')
    
    context = {
        'project': project,
        'materials': materials,
        'material_breakdown': material_breakdown,
    }
    return render(request, 'tracker/project_detail.html', context)


@login_required
def project_create(request):
    """Create a new project."""
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.created_by = request.user
            project.save()
            messages.success(request, f'Project "{project.name}" created successfully!')
            return redirect('project_detail', pk=project.pk)
    else:
        form = ProjectForm()
    
    return render(request, 'tracker/project_form.html', {'form': form, 'title': 'Create Project'})


@login_required
def project_update(request, pk):
    """Update an existing project."""
    project = get_object_or_404(Project, pk=pk)
    
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, f'Project "{project.name}" updated successfully!')
            return redirect('project_detail', pk=project.pk)
    else:
        form = ProjectForm(instance=project)
    
    return render(request, 'tracker/project_form.html', {
        'form': form, 
        'title': 'Update Project',
        'project': project
    })


@login_required
def project_delete(request, pk):
    """Delete a project."""
    project = get_object_or_404(Project, pk=pk)
    
    if request.method == 'POST':
        project_name = project.name
        project.delete()
        messages.success(request, f'Project "{project_name}" deleted successfully!')
        return redirect('project_list')
    
    return render(request, 'tracker/project_confirm_delete.html', {'project': project})


@login_required
def material_create(request, project_pk):
    """Create a new material entry for a project."""
    project = get_object_or_404(Project, pk=project_pk)
    
    if request.method == 'POST':
        form = MaterialEntryForm(request.POST)
        if form.is_valid():
            material = form.save(commit=False)
            material.project = project
            material.created_by = request.user
            material.save()
            messages.success(request, 'Material entry added successfully!')
            return redirect('project_detail', pk=project.pk)
    else:
        form = MaterialEntryForm()
    
    return render(request, 'tracker/material_form.html', {
        'form': form,
        'project': project,
        'title': 'Add Material'
    })


@login_required
def material_update(request, pk):
    """Update an existing material entry."""
    material = get_object_or_404(MaterialEntry, pk=pk)
    project = material.project
    
    if request.method == 'POST':
        form = MaterialEntryForm(request.POST, instance=material)
        if form.is_valid():
            form.save()
            messages.success(request, 'Material entry updated successfully!')
            return redirect('project_detail', pk=project.pk)
    else:
        form = MaterialEntryForm(instance=material)
    
    return render(request, 'tracker/material_form.html', {
        'form': form,
        'project': project,
        'title': 'Update Material',
        'material': material
    })


@login_required
def material_delete(request, pk):
    """Delete a material entry."""
    material = get_object_or_404(MaterialEntry, pk=pk)
    project = material.project
    
    if request.method == 'POST':
        material.delete()
        messages.success(request, 'Material entry deleted successfully!')
        return redirect('project_detail', pk=project.pk)
    
    return render(request, 'tracker/material_confirm_delete.html', {
        'material': material,
        'project': project
    })


@login_required
def receipt_upload(request, material_pk):
    """Upload a receipt for a material entry."""
    material = get_object_or_404(MaterialEntry, pk=material_pk)
    
    # Check if receipt already exists
    if hasattr(material, 'receipt'):
        messages.warning(request, 'This material entry already has a receipt. Delete it first to upload a new one.')
        return redirect('project_detail', pk=material.project.pk)
    
    if request.method == 'POST':
        form = ReceiptUploadForm(request.POST, request.FILES)
        if form.is_valid():
            receipt = form.save(commit=False)
            receipt.material_entry = material
            receipt.save()
            
            # Update material entry
            material.has_receipt = True
            material.save()
            
            messages.success(request, 'Receipt uploaded successfully!')
            return redirect('project_detail', pk=material.project.pk)
    else:
        form = ReceiptUploadForm()
    
    return render(request, 'tracker/receipt_upload.html', {
        'form': form,
        'material': material,
        'project': material.project
    })


@login_required
def receipt_view(request, pk):
    """View or download a receipt."""
    receipt = get_object_or_404(Receipt, pk=pk)
    
    if receipt.file:
        try:
            return FileResponse(
                receipt.file.open('rb'),
                content_type='application/octet-stream',
                as_attachment=False,
                filename=receipt.original_filename
            )
        except Exception as e:
            raise Http404("Receipt file not found.")
    else:
        raise Http404("Receipt file not found.")


@login_required
def receipt_download(request, pk):
    """Download a receipt."""
    receipt = get_object_or_404(Receipt, pk=pk)
    
    if receipt.file:
        try:
            return FileResponse(
                receipt.file.open('rb'),
                content_type='application/octet-stream',
                as_attachment=True,
                filename=receipt.original_filename
            )
        except Exception as e:
            raise Http404("Receipt file not found.")
    else:
        raise Http404("Receipt file not found.")


@login_required
def receipt_delete(request, pk):
    """Delete a receipt."""
    receipt = get_object_or_404(Receipt, pk=pk)
    material = receipt.material_entry
    project = material.project
    
    if request.method == 'POST':
        receipt.delete()
        
        # Update material entry
        material.has_receipt = False
        material.save()
        
        messages.success(request, 'Receipt deleted successfully!')
        return redirect('project_detail', pk=project.pk)
    
    return render(request, 'tracker/receipt_confirm_delete.html', {
        'receipt': receipt,
        'material': material,
        'project': project
    })


@login_required
def dashboard(request):
    """Dashboard with overview of all projects."""
    projects = Project.objects.filter(created_by=request.user)
    
    # Summary statistics
    total_projects = projects.count()
    active_projects = projects.filter(status='in_progress').count()
    completed_projects = projects.filter(status='completed').count()
    total_budget = projects.aggregate(Sum('budget'))['budget__sum'] or 0
    total_spent = sum(p.total_spent for p in projects)
    
    # Recent materials
    recent_materials = MaterialEntry.objects.filter(
        project__created_by=request.user
    ).order_by('-created_at')[:5]
    
    context = {
        'total_projects': total_projects,
        'active_projects': active_projects,
        'completed_projects': completed_projects,
        'total_budget': total_budget,
        'total_spent': total_spent,
        'recent_materials': recent_materials,
        'projects': projects[:5],  # Latest 5 projects
    }
    return render(request, 'tracker/dashboard.html', context)