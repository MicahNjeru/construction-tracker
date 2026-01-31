from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncMonth
from django.http import HttpResponse, FileResponse, Http404
from .models import Project, MaterialEntry, Receipt, MaterialUnit
from .forms import ProjectForm, MaterialEntryForm, ReceiptUploadForm
from django.http import FileResponse, Http404
import os
from datetime import datetime, timedelta

# Create your views here.


@login_required
def project_list(request):
    """Display list of all projects with search."""
    projects = Project.objects.filter(created_by=request.user)
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        projects = projects.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(location__icontains=search_query)
        )
    
    # Status filter
    status_filter = request.GET.get('status', '')
    if status_filter:
        projects = projects.filter(status=status_filter)
    
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
        'search_query': search_query,
        'status_filter': status_filter,
        'status_choices': Project.STATUS_CHOICES,
    }
    return render(request, 'tracker/project_list.html', context)


@login_required
def project_detail(request, pk):
    """Display project details and materials with filtering."""
    project = get_object_or_404(Project, pk=pk)
    materials = project.material_entries.all()
    
    # Search materials
    search_query = request.GET.get('search', '')
    if search_query:
        materials = materials.filter(
            Q(description__icontains=search_query) |
            Q(supplier__icontains=search_query) |
            Q(notes__icontains=search_query)
        )
    
    # Filter by material type
    type_filter = request.GET.get('type', '')
    if type_filter:
        materials = materials.filter(material_type=type_filter)
    
    # Filter by date range
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        materials = materials.filter(purchase_date__gte=date_from)
    if date_to:
        materials = materials.filter(purchase_date__lte=date_to)
    
    # Material breakdown by type
    material_breakdown = project.material_entries.values('material_type').annotate(
        total_cost=Sum('cost'),
        count=Count('id')
    ).order_by('-total_cost')
    
    context = {
        'project': project,
        'materials': materials,
        'material_breakdown': material_breakdown,
        'search_query': search_query,
        'type_filter': type_filter,
        'date_from': date_from,
        'date_to': date_to,
        'material_types': MaterialEntry.MATERIAL_TYPES,
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
    """Upload a receipt for a material entry - Phase 2: Multiple receipts supported."""
    material = get_object_or_404(MaterialEntry, pk=material_pk)
    
    if request.method == 'POST':
        form = ReceiptUploadForm(request.POST, request.FILES)
        if form.is_valid():
            receipt = form.save(commit=False)
            receipt.material_entry = material
            receipt.save()
            
            messages.success(request, 'Receipt uploaded successfully!')
            return redirect('project_detail', pk=material.project.pk)
    else:
        form = ReceiptUploadForm()
    
    return render(request, 'tracker/receipt_upload.html', {
        'form': form,
        'material': material,
        'project': material.project,
        'existing_receipts': material.receipts.all()
    })


@login_required
def receipt_gallery(request, material_pk):
    """View all receipts for a material entry in gallery format."""
    material = get_object_or_404(MaterialEntry, pk=material_pk)
    receipts = material.receipts.all()
    
    context = {
        'material': material,
        'project': material.project,
        'receipts': receipts,
    }
    return render(request, 'tracker/receipt_gallery.html', context)


@login_required
def receipt_set_primary(request, pk):
    """Set a receipt as primary."""
    receipt = get_object_or_404(Receipt, pk=pk)
    
    # Unmark all other receipts as primary
    receipt.material_entry.receipts.update(is_primary=False)
    
    # Mark this one as primary
    receipt.is_primary = True
    receipt.save()
    
    messages.success(request, 'Primary receipt updated!')
    return redirect('receipt_gallery', material_pk=receipt.material_entry.pk)


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
        messages.success(request, 'Receipt deleted successfully!')
        
        # Redirect to gallery if there are more receipts, otherwise to project detail
        if material.receipts.exists():
            return redirect('receipt_gallery', material_pk=material.pk)
        else:
            return redirect('project_detail', pk=project.pk)
    
    return render(request, 'tracker/receipt_confirm_delete.html', {
        'receipt': receipt,
        'material': material,
        'project': project
    })


@login_required
def dashboard(request):
    """Dashboard with overview and analytics - Phase 2: Enhanced."""
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
    
    # Material type breakdown (across all projects)
    material_type_stats = MaterialEntry.objects.filter(
        project__created_by=request.user
    ).values('material_type').annotate(
        total_cost=Sum('cost'),
        count=Count('id')
    ).order_by('-total_cost')[:5]
    
    # Monthly spending (last 6 months)
    six_months_ago = datetime.now().date() - timedelta(days=180)
    monthly_spending = (
        MaterialEntry.objects.filter(
            project__created_by=request.user,
            purchase_date__gte=six_months_ago
        )
        .annotate(month=TruncMonth('purchase_date'))
        .values('month')
        .annotate(total=Sum('cost'))
        .order_by('month')
    )
    
    context = {
        'total_projects': total_projects,
        'active_projects': active_projects,
        'completed_projects': completed_projects,
        'total_budget': total_budget,
        'total_spent': total_spent,
        'recent_materials': recent_materials,
        'projects': projects[:5],
        'material_type_stats': material_type_stats,
        'monthly_spending': monthly_spending,
    }
    return render(request, 'tracker/dashboard.html', context)


@login_required
def export_project_excel(request, pk):
    """Export project materials to Excel."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment
    except ImportError:
        messages.error(request, 'openpyxl is required for Excel export. Install with: pip install openpyxl')
        return redirect('project_detail', pk=pk)
    
    project = get_object_or_404(Project, pk=pk)
    materials = project.material_entries.all()
    
    # Create workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Materials"
    
    # Header styling
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    
    # Headers
    headers = ['Date', 'Type', 'Description', 'Quantity', 'Unit', 'Cost', 'Supplier', 'Has Receipt', 'Notes']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center')
    
    # Data
    for row, material in enumerate(materials, 2):
        ws.cell(row=row, column=1, value=material.purchase_date.strftime('%Y-%m-%d'))
        ws.cell(row=row, column=2, value=material.get_material_type_display())
        ws.cell(row=row, column=3, value=material.description)
        ws.cell(row=row, column=4, value=float(material.quantity))
        ws.cell(row=row, column=5, value=material.unit.abbreviation)
        ws.cell(row=row, column=6, value=float(material.cost))
        ws.cell(row=row, column=7, value=material.supplier)
        ws.cell(row=row, column=8, value='Yes' if material.has_receipt else 'No')
        ws.cell(row=row, column=9, value=material.notes)
    
    # Summary
    summary_row = len(materials) + 3
    ws.cell(row=summary_row, column=5, value="TOTAL:").font = Font(bold=True)
    ws.cell(row=summary_row, column=6, value=float(project.total_spent)).font = Font(bold=True)
    
    # Adjust column widths
    ws.column_dimensions['A'].width = 12
    ws.column_dimensions['B'].width = 15
    ws.column_dimensions['C'].width = 40
    ws.column_dimensions['D'].width = 10
    ws.column_dimensions['E'].width = 8
    ws.column_dimensions['F'].width = 12
    ws.column_dimensions['G'].width = 25
    ws.column_dimensions['H'].width = 12
    ws.column_dimensions['I'].width = 30
    
    # Create response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f"{project.name.replace(' ', '_')}_materials_{datetime.now().strftime('%Y%m%d')}.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    wb.save(response)
    return response


@login_required
def export_project_pdf(request, pk):
    """Export project summary to PDF."""
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.units import inch
    except ImportError:
        messages.error(request, 'reportlab is required for PDF export. Install with: pip install reportlab')
        return redirect('project_detail', pk=pk)
    
    project = get_object_or_404(Project, pk=pk)
    materials = project.material_entries.all()
    
    # Create response
    response = HttpResponse(content_type='application/pdf')
    filename = f"{project.name.replace(' ', '_')}_report_{datetime.now().strftime('%Y%m%d')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # Create PDF
    doc = SimpleDocTemplate(response, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=30,
    )
    elements.append(Paragraph(f"Project Report: {project.name}", title_style))
    elements.append(Spacer(1, 0.2 * inch))
    
    # Project details
    details = [
        ['Location:', project.location or 'N/A'],
        ['Status:', project.get_status_display()],
        ['Start Date:', project.start_date.strftime('%Y-%m-%d')],
        ['Budget:', f'${project.budget:,.2f}'],
        ['Total Spent:', f'${project.total_spent:,.2f}'],
        ['Remaining:', f'${project.remaining_budget:,.2f}'],
    ]
    
    details_table = Table(details, colWidths=[2*inch, 4*inch])
    details_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8e8e8')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(details_table)
    elements.append(Spacer(1, 0.3 * inch))
    
    # Materials table
    elements.append(Paragraph("Materials List", styles['Heading2']))
    elements.append(Spacer(1, 0.1 * inch))
    
    material_data = [['Date', 'Type', 'Description', 'Qty', 'Cost']]
    for material in materials:
        material_data.append([
            material.purchase_date.strftime('%Y-%m-%d'),
            material.get_material_type_display(),
            material.description[:40],
            f"{material.quantity} {material.unit.abbreviation}",
            f'${material.cost:,.2f}'
        ])
    
    material_table = Table(material_data, colWidths=[1*inch, 1.2*inch, 2.5*inch, 1*inch, 1*inch])
    material_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#366092')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')])
    ]))
    elements.append(material_table)
    
    # Build PDF
    doc.build(elements)
    return response
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