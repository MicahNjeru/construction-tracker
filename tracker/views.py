from collections import defaultdict
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Sum, Count, Q, F
from django.db.models.functions import TruncMonth
from django.http import HttpResponse, FileResponse, Http404, JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.views import generic
from .models import *
from .forms import *
from labor.models import LaborEntry
from expenses.models import ExpenseEntry, ExpenseCategory
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak


# Create your views here.


# ==================== User Profile ====================

class UserProfileView(LoginRequiredMixin, generic.UpdateView):
    """View and edit user profile."""
    model = UserProfile
    form_class = UserProfileForm
    template_name = 'tracker/user_profile.html'
    context_object_name = 'profile'

    def get_object(self, queryset=None):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Profile updated successfully!')
        return response

    def get_success_url(self):
        return reverse('user_profile')


class DashboardView(LoginRequiredMixin, generic.TemplateView):
    """Dashboard with overview and analytics."""
    template_name = 'tracker/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        projects = Project.objects.filter(created_by=self.request.user)

        # Summary statistics
        total_projects = projects.count()
        active_projects = projects.filter(status='in_progress').count()
        completed_projects = projects.filter(status='completed').count()
        total_budget = projects.aggregate(Sum('budget'))['budget__sum'] or 0
        total_spent = sum(p.total_spent for p in projects)

        # Calculate total material cost
        total_material_cost = MaterialEntry.objects.filter(
            project__created_by=self.request.user
        ).aggregate(total=Sum('cost'))['total'] or Decimal('0.00')

        # Calculate total labor cost
        total_labor_cost = LaborEntry.objects.filter(
            project__created_by=self.request.user
        ).aggregate(
            total=Sum(F('number_of_workers') * F('rate_per_worker_per_day') * F('number_of_days'))
        )['total'] or Decimal('0.00')

        # Calculate total expense cost
        total_expense_cost = ExpenseEntry.objects.filter(
            project__created_by=self.request.user
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # Recent materials entries
        recent_materials = MaterialEntry.objects.filter(
            project__created_by=self.request.user
        ).select_related('project', 'category').order_by('-created_at')[:5]

        # Recent labor entries
        recent_labor = LaborEntry.objects.filter(
            project__created_by=self.request.user
        ).select_related('project', 'category').order_by('-work_date', '-created_at')[:5]

        # Recent expense entries
        recent_expenses = ExpenseEntry.objects.filter(
            project__created_by=self.request.user
        ).select_related('project', 'category').order_by('-expense_date', '-created_at')[:5]

        # Material type breakdown by category
        material_type_stats = MaterialEntry.objects.filter(
            project__created_by=self.request.user
        ).values('category__name').annotate(
            total_cost=Sum('cost'),
            count=Count('id')
        ).order_by('-total_cost')[:5]

        # Labor breakdown by category
        labor_breakdown = LaborEntry.objects.filter(
            project__created_by=self.request.user
        ).values('category__name').annotate(
            total_cost=Sum(F('number_of_workers') * F('rate_per_worker_per_day') * F('number_of_days')),
            count=Count('id')
        ).order_by('-total_cost')[:5]

        # Expense breakdown by category
        expense_breakdown = ExpenseEntry.objects.filter(
            project__created_by=self.request.user
        ).values('category__name').annotate(
            total_cost=Sum('amount'),
            count=Count('id')
        ).order_by('-total_cost')[:5]

        # Monthly spending
        # ---- Materials grouped by month ----
        materials_monthly = (
            MaterialEntry.objects
            .filter(project__created_by=self.request.user)
            .annotate(month=TruncMonth('purchase_date'))
            .values('month')
            .annotate(material_cost=Sum('cost'))
        )

        # ---- Labor grouped by month ----
        labor_monthly = (
            LaborEntry.objects
            .filter(project__created_by=self.request.user)
            .annotate(month=TruncMonth('work_date'))
            .values('month')
            .annotate(
                labor_cost=Sum(F('number_of_workers') * F('rate_per_worker_per_day') * F('number_of_days'))
            )
        )

        # ---- Expenses grouped by month ----
        expenses_monthly = (
            ExpenseEntry.objects
            .filter(project__created_by=self.request.user)
            .annotate(month=TruncMonth('expense_date'))
            .values('month')
            .annotate(expense_cost=Sum('amount'))
        )

        # ---- Merge into single timeline ----
        monthly_map = defaultdict(lambda: {
            'material_cost': 0,
            'labor_cost': 0,
            'expense_cost': 0
        })

        for row in materials_monthly:
            monthly_map[row['month']]['material_cost'] = row['material_cost']

        for row in labor_monthly:
            monthly_map[row['month']]['labor_cost'] = row['labor_cost']

        for row in expenses_monthly:
            monthly_map[row['month']]['expense_cost'] = row['expense_cost']

        monthly_spending = [
            {
                'month': month,
                'material_cost': data['material_cost'],
                'labor_cost': data['labor_cost'],
                'expense_cost': data['expense_cost'],
            }
            for month, data in sorted(monthly_map.items())
        ]

        context.update({
            'total_projects': total_projects,
            'active_projects': active_projects,
            'completed_projects': completed_projects,
            'total_budget': total_budget,
            'total_spent': total_spent,
            'total_material_cost': total_material_cost,
            'total_labor_cost': total_labor_cost,
            'total_expense_cost': total_expense_cost,
            'recent_materials': recent_materials,
            'recent_labor': recent_labor,
            'recent_expenses': recent_expenses,
            'labor_breakdown': labor_breakdown,
            'expense_breakdown': expense_breakdown,
            'projects': projects[:5],
            'material_type_stats': material_type_stats,
            'monthly_spending': monthly_spending,
        })
        return context


class ProjectListView(LoginRequiredMixin, generic.ListView):
    """Display list of all projects with search."""
    model = Project
    template_name = 'tracker/project_list.html'
    context_object_name = 'projects'

    def get_queryset(self):
        projects = Project.objects.filter(created_by=self.request.user)

        self.search_query = self.request.GET.get('search', '')
        if self.search_query:
            projects = projects.filter(
                Q(name__icontains=self.search_query) |
                Q(description__icontains=self.search_query) |
                Q(location__icontains=self.search_query)
            )

        self.status_filter = self.request.GET.get('status', '')
        if self.status_filter:
            projects = projects.filter(status=self.status_filter)

        return projects

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        projects = context['projects']

        context.update({
            'total_projects': projects.count(),
            'active_projects': projects.filter(status='in_progress').count(),
            'completed_projects': projects.filter(status='completed').count(),
            'total_budget': projects.aggregate(Sum('budget'))['budget__sum'] or 0,
            'search_query': self.search_query,
            'status_filter': self.status_filter,
            'status_choices': Project.STATUS_CHOICES,
        })
        return context


class ProjectDetailView(LoginRequiredMixin, generic.DetailView):
    """Display project details with materials, labor, and expenses with filtering."""
    model = Project
    template_name = 'tracker/project_detail.html'
    context_object_name = 'project'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.object

        materials = project.material_entries.all()
        labor_entries = project.labor_entries.all()
        expense_entries = project.expense_entries.select_related('category').all()

        # Search materials
        search_query = self.request.GET.get('search', '')
        if search_query:
            materials = materials.filter(
                Q(description__icontains=search_query) |
                Q(supplier__icontains=search_query) |
                Q(notes__icontains=search_query)
            )

        # Filter by material type
        type_filter = self.request.GET.get('type', '')
        if type_filter:
            materials = materials.filter(category=type_filter)

        # Filter by date range
        date_from = self.request.GET.get('date_from', '')
        date_to = self.request.GET.get('date_to', '')
        if date_from:
            materials = materials.filter(purchase_date__gte=date_from)
        if date_to:
            materials = materials.filter(purchase_date__lte=date_to)

        # Material breakdown by category
        material_breakdown = project.material_entries.values('category__name').annotate(
            total=Sum('cost'),
            count=Count('id')
        ).order_by('-total')

        # Labor breakdown by category
        labor_breakdown = project.labor_entries.values('category__name').annotate(
            total_cost=Sum(F('number_of_workers') * F('rate_per_worker_per_day') * F('number_of_days')),
            days=Count('id')
        ).order_by('-total_cost')

        # Expense breakdown by category
        expense_breakdown = project.expense_entries.values('category__name').annotate(
            total_amount=Sum('amount'),
            count=Count('id')
        ).order_by('-total_amount')

        context.update({
            'materials': materials,
            'labor_entries': labor_entries,
            'expense_entries': expense_entries,
            'material_breakdown': material_breakdown,
            'labor_breakdown': labor_breakdown,
            'expense_breakdown': expense_breakdown,
            'total_material_cost': project.total_material_cost,
            'total_labor_cost': project.total_labor_cost,
            'total_expense_cost': project.total_expense_cost,
            'search_query': search_query,
            'type_filter': type_filter,
            'date_from': date_from,
            'date_to': date_to,
            'material_categories': MaterialCategory.objects.all(),
        })
        return context


class ProjectCreateView(LoginRequiredMixin, generic.CreateView):
    """Create a new project."""
    model = Project
    form_class = ProjectForm
    template_name = 'tracker/project_form.html'

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f'Project "{self.object.name}" created successfully!')
        return response

    def get_success_url(self):
        return reverse('project_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Project'
        return context


class ProjectUpdateView(LoginRequiredMixin, generic.UpdateView):
    """Update an existing project."""
    model = Project
    form_class = ProjectForm
    template_name = 'tracker/project_form.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Project "{self.object.name}" updated successfully!')
        return response

    def get_success_url(self):
        return reverse('project_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update Project'
        context['project'] = self.object
        return context


class ProjectDeleteView(LoginRequiredMixin, generic.DeleteView):
    """Delete a project."""
    model = Project
    template_name = 'tracker/project_confirm_delete.html'
    context_object_name = 'project'

    def form_valid(self, form):
        project_name = self.object.name
        self.object.delete()
        messages.success(self.request, f'Project "{project_name}" deleted successfully!')
        return redirect('project_list')


# ==================== Materials ====================

class MaterialCreateView(LoginRequiredMixin, generic.CreateView):
    """Create a new material entry for a project."""
    model = MaterialEntry
    form_class = MaterialEntryForm
    template_name = 'tracker/material_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(Project, pk=kwargs['project_pk'])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.project = self.project
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        material = self.object

        # Handle optional receipt upload
        receipt_file = self.request.FILES.get('receipt_file')
        if receipt_file:
            Receipt.objects.create(
                material_entry=material,
                file=receipt_file,
                original_filename=receipt_file.name,
                file_size=receipt_file.size,
                is_primary=bool(self.request.POST.get('receipt_is_primary')),
                notes=self.request.POST.get('receipt_notes', '').strip()
            )

        ActivityLog.objects.create(
            project=self.project,
            user=self.request.user,
            action='material_added',
            description=f"Added {material.category.name}: {material.description}",
            related_material=material
        )
        check_budget_alerts(self.project)
        messages.success(self.request, 'Material entry added successfully!')
        return response

    def get_success_url(self):
        return reverse('project_detail', kwargs={'pk': self.project.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.project
        context['title'] = 'Add Material'
        return context


class MaterialUpdateView(LoginRequiredMixin, generic.UpdateView):
    """Update an existing material entry."""
    model = MaterialEntry
    form_class = MaterialEntryForm
    template_name = 'tracker/material_form.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        material = self.object
        project = material.project

        # Handle optional receipt upload
        receipt_file = self.request.FILES.get('receipt_file')
        if receipt_file:
            Receipt.objects.create(
                material_entry=material,
                file=receipt_file,
                original_filename=receipt_file.name,
                file_size=receipt_file.size,
                is_primary=bool(self.request.POST.get('receipt_is_primary')),
                notes=self.request.POST.get('receipt_notes', '').strip()
            )

        ActivityLog.objects.create(
            project=project,
            user=self.request.user,
            action='material_updated',
            description=f"Updated {material.category.name}: {material.description}",
            related_material=material
        )
        check_budget_alerts(project)
        messages.success(self.request, 'Material entry updated successfully!')
        return response

    def get_success_url(self):
        return reverse('project_detail', kwargs={'pk': self.object.project.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project
        context['title'] = 'Update Material'
        context['material'] = self.object
        return context


class MaterialDeleteView(LoginRequiredMixin, generic.DeleteView):
    """Delete a material entry."""
    model = MaterialEntry
    template_name = 'tracker/material_confirm_delete.html'
    context_object_name = 'material'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project
        return context

    def form_valid(self, form):
        material = self.object
        project = material.project

        ActivityLog.objects.create(
            project=project,
            user=self.request.user,
            action='material_deleted',
            description=f"Deleted {material.category.name}: {material.description}"
        )
        material.delete()
        messages.success(self.request, 'Material entry deleted successfully!')
        return redirect('project_detail', pk=project.pk)


# ==================== Receipts ====================

class ReceiptUploadView(LoginRequiredMixin, generic.CreateView):
    """Upload a receipt for a material entry - Phase 2: Multiple receipts supported."""
    model = Receipt
    form_class = ReceiptUploadForm
    template_name = 'tracker/receipt_upload.html'

    def dispatch(self, request, *args, **kwargs):
        self.material = get_object_or_404(MaterialEntry, pk=kwargs['material_pk'])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.material_entry = self.material
        response = super().form_valid(form)
        messages.success(self.request, 'Receipt uploaded successfully!')
        return response

    def get_success_url(self):
        return reverse('project_detail', kwargs={'pk': self.material.project.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['material'] = self.material
        context['project'] = self.material.project
        context['existing_receipts'] = self.material.receipts.all()
        return context


class ReceiptGalleryView(LoginRequiredMixin, generic.DetailView):
    """View all receipts for a material entry in gallery format."""
    model = MaterialEntry
    pk_url_kwarg = 'material_pk'
    template_name = 'tracker/receipt_gallery.html'
    context_object_name = 'material'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project
        context['receipts'] = self.object.receipts.all()
        return context


class ReceiptSetPrimaryView(LoginRequiredMixin, generic.View):
    """Set a receipt as primary."""

    def get(self, request, pk, *args, **kwargs):
        receipt = get_object_or_404(Receipt, pk=pk)

        # Unmark all other receipts as primary
        receipt.material_entry.receipts.update(is_primary=False)

        # Mark this one as primary
        receipt.is_primary = True
        receipt.save()

        messages.success(request, 'Primary receipt updated!')
        return redirect('receipt_gallery', material_pk=receipt.material_entry.pk)


class ReceiptViewView(LoginRequiredMixin, generic.View):
    """View or download a receipt."""

    def get(self, request, pk, *args, **kwargs):
        receipt = get_object_or_404(Receipt, pk=pk)

        if receipt.file:
            try:
                return FileResponse(
                    receipt.file.open('rb'),
                    content_type='application/octet-stream',
                    as_attachment=False,
                    filename=receipt.original_filename
                )
            except Exception:
                raise Http404("Receipt file not found.")
        else:
            raise Http404("Receipt file not found.")


class ReceiptDownloadView(LoginRequiredMixin, generic.View):
    """Download a receipt."""

    def get(self, request, pk, *args, **kwargs):
        receipt = get_object_or_404(Receipt, pk=pk)

        if receipt.file:
            try:
                return FileResponse(
                    receipt.file.open('rb'),
                    content_type='application/octet-stream',
                    as_attachment=True,
                    filename=receipt.original_filename
                )
            except Exception:
                raise Http404("Receipt file not found.")
        else:
            raise Http404("Receipt file not found.")


class ReceiptDeleteView(LoginRequiredMixin, generic.DeleteView):
    """Delete a receipt."""
    model = Receipt
    template_name = 'tracker/receipt_confirm_delete.html'
    context_object_name = 'receipt'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['material'] = self.object.material_entry
        context['project'] = self.object.material_entry.project
        return context

    def form_valid(self, form):
        material = self.object.material_entry
        project = material.project
        self.object.delete()
        messages.success(self.request, 'Receipt deleted successfully!')

        # Redirect to gallery if there are more receipts, otherwise to project detail
        if material.receipts.exists():
            return redirect('receipt_gallery', material_pk=material.pk)
        else:
            return redirect('project_detail', pk=project.pk)


# ==================== Exports ====================

class ExportProjectExcelView(LoginRequiredMixin, generic.View):
    """Export project data to Excel"""

    def get(self, request, pk, *args, **kwargs):
        project = get_object_or_404(Project, pk=pk)

        # Create workbook
        wb = Workbook()

        # Define styles
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=12)
        title_font = Font(bold=True, size=14)
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )

        # ===== PROJECT SUMMARY SHEET =====
        ws_summary = wb.active
        ws_summary.title = "Project Summary"

        # Project header
        ws_summary['A1'] = "PROJECT SUMMARY"
        ws_summary['A1'].font = title_font
        ws_summary.merge_cells('A1:B1')

        # Project details
        summary_data = [
            ("Project Name:", project.name),
            ("Location:", project.location or "N/A"),
            ("Status:", project.get_status_display()),
            ("Start Date:", project.start_date.strftime('%Y-%m-%d')),
            ("End Date:", project.end_date.strftime('%Y-%m-%d') if project.end_date else "N/A"),
            ("", ""),
            ("FINANCIAL SUMMARY", ""),
            ("Budget:", f"Ksh {project.budget:,.2f}"),
            ("Total Material Cost:", f"Ksh {project.total_material_cost:,.2f}"),
            ("Total Labor Cost:", f"Ksh {project.total_labor_cost:,.2f}"),
            ("Total Expenses:", f"Ksh {project.total_expense_cost:,.2f}"),
            ("Total Spent:", f"Ksh {project.total_spent:,.2f}"),
            ("Remaining Budget:", f"Ksh {project.remaining_budget:,.2f}"),
            ("Budget Utilization:", f"{project.budget_utilization_percentage:.2f}%"),
        ]

        row = 3
        for label, value in summary_data:
            ws_summary[f'A{row}'] = label
            ws_summary[f'B{row}'] = value
            if label in ["FINANCIAL SUMMARY", "PROJECT SUMMARY"]:
                ws_summary[f'A{row}'].font = Font(bold=True, size=12)
            else:
                ws_summary[f'A{row}'].font = Font(bold=True)
            row += 1

        # Adjust column widths
        ws_summary.column_dimensions['A'].width = 25
        ws_summary.column_dimensions['B'].width = 40

        # ===== MATERIALS SHEET =====
        ws_materials = wb.create_sheet("Materials")

        # Headers
        material_headers = [
            "Date", "Category", "Description", "Quantity", "Unit",
            "Cost", "Unit Cost", "Supplier", "Qty Used", "Qty Remaining", "Notes"
        ]

        for col_num, header in enumerate(material_headers, 1):
            cell = ws_materials.cell(row=1, column=col_num)
            cell.value = header
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = border

        # Data
        materials = project.material_entries.select_related('category', 'unit').all()
        for row_num, material in enumerate(materials, 2):
            ws_materials.cell(row=row_num, column=1).value = material.purchase_date.strftime('%Y-%m-%d')
            ws_materials.cell(row=row_num, column=2).value = material.category.name
            ws_materials.cell(row=row_num, column=3).value = material.description
            ws_materials.cell(row=row_num, column=4).value = float(material.quantity)
            ws_materials.cell(row=row_num, column=5).value = material.unit.abbreviation
            ws_materials.cell(row=row_num, column=6).value = float(material.cost)
            ws_materials.cell(row=row_num, column=7).value = float(material.unit_cost)
            ws_materials.cell(row=row_num, column=8).value = material.supplier or "N/A"
            ws_materials.cell(row=row_num, column=9).value = float(material.quantity_used)
            ws_materials.cell(row=row_num, column=10).value = float(material.quantity_remaining)
            ws_materials.cell(row=row_num, column=11).value = material.notes or ""

            # Apply borders
            for col in range(1, 12):
                ws_materials.cell(row=row_num, column=col).border = border

        # Adjust column widths
        ws_materials.column_dimensions['A'].width = 12
        ws_materials.column_dimensions['B'].width = 15
        ws_materials.column_dimensions['C'].width = 30
        ws_materials.column_dimensions['D'].width = 10
        ws_materials.column_dimensions['E'].width = 8
        ws_materials.column_dimensions['F'].width = 12
        ws_materials.column_dimensions['G'].width = 12
        ws_materials.column_dimensions['H'].width = 20
        ws_materials.column_dimensions['I'].width = 10
        ws_materials.column_dimensions['J'].width = 12
        ws_materials.column_dimensions['K'].width = 30

        # ===== LABOR SHEET =====
        ws_labor = wb.create_sheet("Labor")

        # Headers
        labor_headers = [
            "Date", "Category", "Description", "Workers",
            "Rate/Worker/Day", "Total Cost", "Notes"
        ]

        for col_num, header in enumerate(labor_headers, 1):
            cell = ws_labor.cell(row=1, column=col_num)
            cell.value = header
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = border

        # Data
        labor_entries = project.labor_entries.select_related('category').all()
        for row_num, labor in enumerate(labor_entries, 2):
            ws_labor.cell(row=row_num, column=1).value = labor.work_date.strftime('%Y-%m-%d')
            ws_labor.cell(row=row_num, column=2).value = labor.category.name
            ws_labor.cell(row=row_num, column=3).value = labor.number_of_workers
            ws_labor.cell(row=row_num, column=4).value = float(labor.rate_per_worker_per_day)
            ws_labor.cell(row=row_num, column=5).value = float(labor.total_cost)
            ws_labor.cell(row=row_num, column=6).value = labor.notes or ""

            # Apply borders
            for col in range(1, 8):
                ws_labor.cell(row=row_num, column=col).border = border

        # Adjust column widths
        ws_labor.column_dimensions['A'].width = 12
        ws_labor.column_dimensions['B'].width = 15
        ws_labor.column_dimensions['C'].width = 30
        ws_labor.column_dimensions['D'].width = 10
        ws_labor.column_dimensions['E'].width = 15
        ws_labor.column_dimensions['F'].width = 12

        # ===== EXPENSES SHEET =====
        ws_expenses = wb.create_sheet("Expenses")

        # Headers
        expense_headers = [
            "Date", "Category", "Description", "Amount",
            "Payment Method", "Payee", "Notes"
        ]

        for col_num, header in enumerate(expense_headers, 1):
            cell = ws_expenses.cell(row=1, column=col_num)
            cell.value = header
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = border

        # Data
        expense_entries = project.expense_entries.select_related('category').all()
        for row_num, expense in enumerate(expense_entries, 2):
            ws_expenses.cell(row=row_num, column=1).value = expense.expense_date.strftime('%Y-%m-%d')
            ws_expenses.cell(row=row_num, column=2).value = expense.category.name
            ws_expenses.cell(row=row_num, column=3).value = expense.description
            ws_expenses.cell(row=row_num, column=4).value = float(expense.amount)
            ws_expenses.cell(row=row_num, column=5).value = expense.get_payment_method_display()
            ws_expenses.cell(row=row_num, column=6).value = expense.payee or "N/A"
            ws_expenses.cell(row=row_num, column=7).value = expense.notes or ""

            # Apply borders
            for col in range(1, 8):
                ws_expenses.cell(row=row_num, column=col).border = border

        # Adjust column widths
        ws_expenses.column_dimensions['A'].width = 12
        ws_expenses.column_dimensions['B'].width = 15
        ws_expenses.column_dimensions['C'].width = 30
        ws_expenses.column_dimensions['D'].width = 12
        ws_expenses.column_dimensions['E'].width = 15
        ws_expenses.column_dimensions['F'].width = 20
        ws_expenses.column_dimensions['G'].width = 30

        # Create response
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{project.name}_report.xlsx"'

        wb.save(response)
        return response


class ExportProjectPDFView(LoginRequiredMixin, generic.View):
    """Export project data to PDF including materials, labor, and expenses."""

    def get(self, request, pk, *args, **kwargs):
        project = get_object_or_404(Project, pk=pk)

        # Create response
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{project.name}_report.pdf"'

        # Create PDF document - landscape for better table viewing
        doc = SimpleDocTemplate(response, pagesize=landscape(A4),
                               rightMargin=30, leftMargin=30,
                               topMargin=30, bottomMargin=18)

        # Container for elements
        elements = []

        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#366092'),
            spaceAfter=30,
            alignment=TA_CENTER
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#366092'),
            spaceAfter=12,
            spaceBefore=12
        )

        # Title
        title = Paragraph(f"Project Report: {project.name}", title_style)
        elements.append(title)
        elements.append(Spacer(1, 0.2*inch))

        # ===== PROJECT SUMMARY =====
        summary_heading = Paragraph("Project Summary", heading_style)
        elements.append(summary_heading)

        summary_data = [
            ["Project Name:", project.name],
            ["Location:", project.location or "N/A"],
            ["Status:", project.get_status_display()],
            ["Start Date:", project.start_date.strftime('%Y-%m-%d')],
            ["End Date:", project.end_date.strftime('%Y-%m-%d') if project.end_date else "N/A"],
        ]

        summary_table = Table(summary_data, colWidths=[2*inch, 4*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 0.3*inch))

        # ===== FINANCIAL SUMMARY =====
        financial_heading = Paragraph("Financial Summary", heading_style)
        elements.append(financial_heading)

        financial_data = [
            ["Budget:", f"Ksh {project.budget:,.2f}"],
            ["Total Material Cost:", f"Ksh {project.total_material_cost:,.2f}"],
            ["Total Labor Cost:", f"Ksh {project.total_labor_cost:,.2f}"],
            ["Total Expenses:", f"Ksh {project.total_expense_cost:,.2f}"],
            ["Total Spent:", f"Ksh {project.total_spent:,.2f}"],
            ["Remaining Budget:", f"Ksh {project.remaining_budget:,.2f}"],
            ["Budget Utilization:", f"{project.budget_utilization_percentage:.2f}%"],
        ]

        financial_table = Table(financial_data, colWidths=[2*inch, 4*inch])
        financial_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            # Highlight total spent row
            ('BACKGROUND', (0, 4), (-1, 4), colors.HexColor('#fffacd')),
            ('FONTNAME', (0, 4), (-1, 4), 'Helvetica-Bold'),
        ]))
        elements.append(financial_table)
        elements.append(Spacer(1, 0.3*inch))

        # ===== MATERIALS =====
        materials = project.material_entries.select_related('category', 'unit').all()
        if materials.exists():
            elements.append(PageBreak())
            materials_heading = Paragraph("Materials", heading_style)
            elements.append(materials_heading)

            # Table headers
            material_data = [
                ["Date", "Category", "Supplier", "Description", "Qty", "Unit", "Cost"]
            ]

            for material in materials:
                material_data.append([
                    material.purchase_date.strftime('%Y-%m-%d'),
                    material.category.name,
                    material.supplier[:20] if material.supplier else "N/A",
                    material.description[:40] + "..." if len(material.description) > 40 else material.description,
                    f"{material.quantity:.2f}",
                    material.unit.abbreviation,
                    f"Ksh {material.cost:,.2f}"
                ])

            # Add total row
            material_data.append([
                "", "", "", "", "",
                "TOTAL:",
                f"Ksh {project.total_material_cost:,.2f}"
            ])

            material_table = Table(material_data, colWidths=[1*inch, 1*inch, 1.4*inch, 2.5*inch, 0.8*inch, 0.8*inch, 1.5*inch])
            material_table.setStyle(TableStyle([
                # Header row
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#366092')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),

                # Data rows
                ('FONTSIZE', (0, 1), (-1, -2), 8),
                ('ALIGN', (3, 1), (3, -2), 'RIGHT'),  # Quantity
                ('ALIGN', (5, 1), (5, -2), 'RIGHT'),  # Cost
                ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f9f9f9')]),

                # Total row
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#fffacd')),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('ALIGN', (5, -1), (5, -1), 'RIGHT'),
                ('SPAN', (0, -1), (4, -1)),
                ('GRID', (0, -1), (-1, -1), 1, colors.grey),
            ]))
            elements.append(material_table)

        # ===== LABOR =====
        labor_entries = project.labor_entries.select_related('category').all()
        if labor_entries.exists():
            elements.append(PageBreak())
            labor_heading = Paragraph("Labor Entries", heading_style)
            elements.append(labor_heading)

            # Table headers
            labor_data = [
                ["Date", "Category", "Notes", "Workers", "Rate/Day", "Total Cost"]
            ]

            for labor in labor_entries:
                labor_data.append([
                    labor.work_date.strftime('%Y-%m-%d'),
                    labor.category.name,
                    labor.notes[:50] + "..." if len(labor.notes) > 50 else labor.notes,
                    str(labor.number_of_workers),
                    f"Ksh {labor.rate_per_worker_per_day:,.2f}",
                    f"Ksh {labor.total_cost:,.2f}"
                ])

            # Add total row
            labor_data.append([
                "", "", "", "",
                "TOTAL:",
                f"Ksh {project.total_labor_cost:,.2f}"
            ])

            labor_table = Table(labor_data, colWidths=[1*inch, 1.5*inch, 3*inch, 1*inch, 1.2*inch, 1.3*inch])
            labor_table.setStyle(TableStyle([
                # Header row
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#366092')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),

                # Data rows
                ('FONTSIZE', (0, 1), (-1, -2), 8),
                ('ALIGN', (3, 1), (3, -2), 'CENTER'),  # Workers
                ('ALIGN', (4, 1), (4, -2), 'RIGHT'),   # Rate
                ('ALIGN', (5, 1), (5, -2), 'RIGHT'),   # Total
                ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f9f9f9')]),

                # Total row
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#fffacd')),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('ALIGN', (4, -1), (4, -1), 'RIGHT'),
                ('ALIGN', (5, -1), (5, -1), 'RIGHT'),
                ('SPAN', (0, -1), (3, -1)),
                ('GRID', (0, -1), (-1, -1), 1, colors.grey),
            ]))
            elements.append(labor_table)

        # ===== EXPENSES =====
        expense_entries = project.expense_entries.select_related('category').all()
        if expense_entries.exists():
            elements.append(PageBreak())
            expense_heading = Paragraph("Expenses", heading_style)
            elements.append(expense_heading)

            # Table headers
            expense_data = [
                ["Date", "Category", "Description", "Payment Method", "Payee", "Amount"]
            ]

            for expense in expense_entries:
                expense_data.append([
                    expense.expense_date.strftime('%Y-%m-%d'),
                    expense.category.name,
                    expense.description[:50] + "..." if len(expense.description) > 50 else expense.description,
                    expense.get_payment_method_display(),
                    expense.payee[:20] if expense.payee else "N/A",
                    f"Ksh {expense.amount:,.2f}"
                ])

            # Add total row
            expense_data.append([
                "", "", "", "",
                "TOTAL:",
                f"Ksh {project.total_expense_cost:,.2f}"
            ])

            expense_table = Table(expense_data, colWidths=[1*inch, 1.3*inch, 2.8*inch, 1.3*inch, 1.3*inch, 1.3*inch])
            expense_table.setStyle(TableStyle([
                # Header row
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#366092')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),

                # Data rows
                ('FONTSIZE', (0, 1), (-1, -2), 8),
                ('ALIGN', (5, 1), (5, -2), 'RIGHT'),  # Amount
                ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f9f9f9')]),

                # Total row
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#fffacd')),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('ALIGN', (4, -1), (4, -1), 'RIGHT'),  # TOTAL label aligned right
                ('ALIGN', (5, -1), (5, -1), 'RIGHT'),  # Amount aligned right
                ('SPAN', (0, -1), (3, -1)),  # Span columns 0-3 (Date, Category, Description, Payment Method)
                ('GRID', (0, -1), (-1, -1), 1, colors.grey),
            ]))
            elements.append(expense_table)

        # Build PDF
        doc.build(elements)

        return response


# ==================== Material Usage Tracking ====================

class MaterialUsageUpdateView(LoginRequiredMixin, generic.FormView):
    """Update material usage quantity."""
    form_class = MaterialUsageForm
    template_name = 'tracker/material_usage_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.material = get_object_or_404(MaterialEntry, pk=kwargs['pk'])
        self.project = self.material.project
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        return {'quantity_used': self.material.quantity_used}

    def form_valid(self, form):
        new_quantity_used = form.cleaned_data['quantity_used']
        usage_notes = form.cleaned_data.get('notes', '')

        # Validate
        if new_quantity_used > self.material.quantity:
            messages.error(self.request, 'Quantity used cannot exceed total quantity!')
            return redirect('project_detail', pk=self.project.pk)

        # Update material
        old_quantity_used = self.material.quantity_used
        self.material.quantity_used = new_quantity_used
        self.material.save()

        # Log activity
        ActivityLog.objects.create(
            project=self.project,
            user=self.request.user,
            action='material_used',
            description=(
                f"Updated usage for {self.material.description}: "
                f"{old_quantity_used} \u2192 {new_quantity_used} {self.material.unit.abbreviation}. {usage_notes}"
            ),
            related_material=self.material
        )

        messages.success(self.request, 'Material usage updated successfully!')
        return redirect('project_detail', pk=self.project.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['material'] = self.material
        context['project'] = self.project
        return context


class QuickUsageUpdateView(LoginRequiredMixin, generic.View):
    """Quick AJAX update for material usage."""

    def post(self, request, pk, *args, **kwargs):
        material = get_object_or_404(MaterialEntry, pk=pk)
        quantity_used = request.POST.get('quantity_used')

        try:
            quantity_used = float(quantity_used)
            if quantity_used < 0 or quantity_used > float(material.quantity):
                return JsonResponse({'success': False, 'error': 'Invalid quantity'})

            material.quantity_used = quantity_used
            material.save()

            return JsonResponse({
                'success': True,
                'quantity_remaining': float(material.quantity_remaining),
                'usage_percentage': float(material.usage_percentage)
            })
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Invalid number'})

    def get(self, request, *args, **kwargs):
        return JsonResponse({'success': False, 'error': 'Invalid request'})


# ==================== Project Templates ====================

class TemplateCreateView(LoginRequiredMixin, generic.CreateView):
    """Create a new project template."""
    model = ProjectTemplate
    form_class = ProjectTemplateForm
    template_name = 'tracker/template_form.html'

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, 'Template created successfully!')
        return response

    def get_success_url(self):
        return reverse('template_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Template'
        return context


class TemplateListView(LoginRequiredMixin, generic.TemplateView):
    """List all templates available to user."""
    template_name = 'tracker/template_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_templates'] = ProjectTemplate.objects.filter(created_by=self.request.user)
        context['public_templates'] = ProjectTemplate.objects.filter(
            is_public=True
        ).exclude(created_by=self.request.user)
        return context


class TemplateDetailView(LoginRequiredMixin, generic.DetailView):
    """View template details and materials."""
    model = ProjectTemplate
    template_name = 'tracker/template_detail.html'
    context_object_name = 'template'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        materials = self.object.materials.all()
        context['materials'] = materials
        context['estimated_total'] = materials.aggregate(Sum('estimated_cost'))['estimated_cost__sum'] or 0
        return context


class TemplateUpdateView(LoginRequiredMixin, generic.UpdateView):
    """Update an existing project template."""
    model = ProjectTemplate
    form_class = ProjectTemplateForm
    template_name = 'tracker/template_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.template = get_object_or_404(ProjectTemplate, pk=kwargs['pk'])
        if self.template.created_by != request.user:
            messages.error(request, 'You do not have permission to edit this template.')
            return redirect('template_list')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Template "{self.object.name}" updated successfully!')
        return response

    def get_success_url(self):
        return reverse('template_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update Template'
        context['template'] = self.object
        return context


class TemplateDeleteView(LoginRequiredMixin, generic.DeleteView):
    """Delete a project template."""
    model = ProjectTemplate
    template_name = 'tracker/template_confirm_delete.html'
    context_object_name = 'template'

    def dispatch(self, request, *args, **kwargs):
        self.template = get_object_or_404(ProjectTemplate, pk=kwargs['pk'])
        if self.template.created_by != request.user:
            messages.error(request, 'You do not have permission to delete this template.')
            return redirect('template_list')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['material_count'] = self.object.materials.count()
        return context

    def form_valid(self, form):
        template_name = self.object.name
        material_count = self.object.materials.count()
        self.object.delete()
        messages.success(
            self.request,
            f'Template "{template_name}" and {material_count} materials deleted successfully!'
        )
        return redirect('template_list')


class TemplateAddMaterialView(LoginRequiredMixin, generic.CreateView):
    """Add material to template."""
    model = TemplateMaterial
    form_class = TemplateMaterialForm
    template_name = 'tracker/template_material_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.template = get_object_or_404(ProjectTemplate, pk=kwargs['template_pk'])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.template = self.template
        response = super().form_valid(form)
        messages.success(self.request, 'Material added to template!')
        return response

    def get_success_url(self):
        return reverse('template_detail', kwargs={'pk': self.template.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['template'] = self.template
        return context


class TemplateMaterialUpdateView(LoginRequiredMixin, generic.UpdateView):
    """Update a material in a template."""
    model = TemplateMaterial
    form_class = TemplateMaterialForm
    pk_url_kwarg = 'material_pk'
    template_name = 'tracker/template_material_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.template = get_object_or_404(ProjectTemplate, pk=kwargs['pk'])
        if self.template.created_by != request.user:
            messages.error(request, 'You do not have permission to edit this template.')
            return redirect('template_list')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return TemplateMaterial.objects.filter(template=self.template)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Template material updated successfully!')
        return response

    def get_success_url(self):
        return reverse('template_detail', kwargs={'pk': self.template.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['template'] = self.template
        context['material'] = self.object
        context['title'] = 'Update Template Material'
        return context


class TemplateMaterialDeleteView(LoginRequiredMixin, generic.DeleteView):
    """Delete a material from a template."""
    model = TemplateMaterial
    pk_url_kwarg = 'material_pk'
    template_name = 'tracker/template_material_confirm_delete.html'
    context_object_name = 'material'

    def dispatch(self, request, *args, **kwargs):
        self.template = get_object_or_404(ProjectTemplate, pk=kwargs['pk'])
        if self.template.created_by != request.user:
            messages.error(request, 'You do not have permission to delete this template.')
            return redirect('template_list')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return TemplateMaterial.objects.filter(template=self.template)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['template'] = self.template
        return context

    def form_valid(self, form):
        material_description = self.object.description
        self.object.delete()
        messages.success(self.request, f'Material "{material_description}" removed from template!')
        return redirect('template_detail', pk=self.template.pk)


class CreateProjectFromTemplateView(LoginRequiredMixin, generic.FormView):
    """Create a new project from a template."""
    form_class = CreateProjectFromTemplateForm
    template_name = 'tracker/create_from_template.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        template = form.cleaned_data['template']

        # Create project
        project = Project.objects.create(
            name=form.cleaned_data['name'],
            location=form.cleaned_data['location'],
            budget=form.cleaned_data['budget'],
            start_date=form.cleaned_data['start_date'],
            created_by=self.request.user,
            created_from_template=template
        )

        # Copy materials from template
        for template_material in template.materials.all():
            MaterialEntry.objects.create(
                project=project,
                category=template_material.category,
                description=template_material.description,
                quantity=template_material.estimated_quantity,
                unit=template_material.unit,
                cost=template_material.estimated_cost,
                purchase_date=form.cleaned_data['start_date'],
                notes=template_material.notes,
                created_by=self.request.user
            )

        # Log activity
        ActivityLog.objects.create(
            project=project,
            user=self.request.user,
            action='project_created',
            description=f"Project created from template '{template.name}' with {template.materials.count()} materials"
        )

        messages.success(
            self.request,
            f'Project created from template with {template.materials.count()} materials!'
        )
        self.project = project
        return redirect('project_detail', pk=project.pk)


# ==================== Project Photos ====================

class ProjectPhotosView(LoginRequiredMixin, generic.ListView):
    """View all photos for a project."""
    model = ProjectPhoto
    template_name = 'tracker/project_photos.html'
    context_object_name = 'photos'

    def get_queryset(self):
        self.project = get_object_or_404(Project, pk=self.kwargs['project_pk'])
        return self.project.photos.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.project
        return context


class PhotoUploadView(LoginRequiredMixin, generic.CreateView):
    """Upload a photo to project gallery."""
    model = ProjectPhoto
    form_class = ProjectPhotoForm
    template_name = 'tracker/photo_upload.html'

    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(Project, pk=kwargs['project_pk'])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.project = self.project
        form.instance.uploaded_by = self.request.user
        if not form.instance.taken_date:
            form.instance.taken_date = timezone.now().date()
        response = super().form_valid(form)

        # Log activity
        ActivityLog.objects.create(
            project=self.project,
            user=self.request.user,
            action='photo_uploaded',
            description=f"Uploaded photo: {self.object.title or 'Untitled'}"
        )

        messages.success(self.request, 'Photo uploaded successfully!')
        return response

    def get_success_url(self):
        return reverse('project_photos', kwargs={'project_pk': self.project.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.project
        return context


class PhotoDeleteView(LoginRequiredMixin, generic.DeleteView):
    """Delete a project photo."""
    model = ProjectPhoto
    template_name = 'tracker/photo_confirm_delete.html'
    context_object_name = 'photo'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project
        return context

    def form_valid(self, form):
        photo = self.object
        project = photo.project

        # Log activity
        ActivityLog.objects.create(
            project=project,
            user=self.request.user,
            action='photo_deleted',
            description=f"Deleted photo: {photo.title or 'Untitled'}"
        )

        photo.delete()
        messages.success(self.request, 'Photo deleted successfully!')
        return redirect('project_photos', project_pk=project.pk)


# ==================== Activity Timeline ====================

class ProjectTimelineView(LoginRequiredMixin, generic.DetailView):
    """View project activity timeline."""
    model = Project
    template_name = 'tracker/project_timeline.html'
    context_object_name = 'project'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['activities'] = self.object.activity_logs.all()[:50]  # Last 50 activities
        return context


# ==================== Budget Alerts ====================

class BudgetAlertsView(LoginRequiredMixin, generic.ListView):
    """View all budget alerts for user's projects."""
    model = BudgetAlert
    template_name = 'tracker/budget_alerts.html'
    context_object_name = 'alerts'

    def get_queryset(self):
        user_projects = Project.objects.filter(created_by=self.request.user)
        return BudgetAlert.objects.filter(
            project__in=user_projects
        ).order_by('-created_at')[:20]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unread_count'] = context['alerts'].filter(is_read=False).count()
        return context


class MarkAlertReadView(LoginRequiredMixin, generic.View):
    """Mark an alert as read."""

    def get(self, request, pk, *args, **kwargs):
        alert = get_object_or_404(BudgetAlert, pk=pk)
        alert.is_read = True
        alert.save()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})

        return redirect('budget_alerts')


# ==================== Helpers (not views) ====================

def check_budget_alerts(project):
    """Helper function to check and create budget alerts."""
    percentage = project.budget_utilization_percentage

    # Check for different alert levels
    if percentage >= 100 and not project.budget_alerts.filter(alert_type='exceeded').exists():
        BudgetAlert.objects.create(
            project=project,
            alert_type='exceeded',
            percentage=percentage,
            message=f"Budget exceeded! Spent Ksh{project.total_spent} of Ksh{project.budget} ({percentage:.1f}%)"
        )
    elif percentage >= 90 and not project.budget_alerts.filter(alert_type='critical').exists():
        BudgetAlert.objects.create(
            project=project,
            alert_type='critical',
            percentage=percentage,
            message=f"Critical: {percentage:.1f}% of budget used (Ksh{project.total_spent} of Ksh{project.budget})"
        )
    elif percentage >= 75 and not project.budget_alerts.filter(alert_type='warning').exists():
        BudgetAlert.objects.create(
            project=project,
            alert_type='warning',
            percentage=percentage,
            message=f"Warning: {percentage:.1f}% of budget used (Ksh{project.total_spent} of Ksh{project.budget})"
        )


