from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Sum, Count
from django.http import JsonResponse
from django.urls import reverse
from django.views import generic
from tracker.models import Project
from .models import ExpenseEntry, ExpenseReceipt, ExpenseCategory
from .forms import ExpenseEntryForm, ExpenseReceiptForm, ExpenseFilterForm

# Create your views here.


class ExpenseListView(LoginRequiredMixin, generic.ListView):
    """List all expenses for a project with filtering"""
    model = ExpenseEntry
    template_name = 'expenses/expense_list.html'
    context_object_name = 'expenses'

    def get_queryset(self):
        self.project = get_object_or_404(
            Project, pk=self.kwargs['project_pk'], created_by=self.request.user
        )
        expenses = ExpenseEntry.objects.filter(project=self.project).select_related(
            'category', 'created_by'
        )

        self.filter_form = ExpenseFilterForm(self.request.GET)
        if self.filter_form.is_valid():
            cd = self.filter_form.cleaned_data
            if cd.get('category'):
                expenses = expenses.filter(category=cd['category'])
            if cd.get('payment_method'):
                expenses = expenses.filter(payment_method=cd['payment_method'])
            if cd.get('date_from'):
                expenses = expenses.filter(expense_date__gte=cd['date_from'])
            if cd.get('date_to'):
                expenses = expenses.filter(expense_date__lte=cd['date_to'])
            if cd.get('has_receipt') is not None:
                expenses = expenses.filter(has_receipt=cd['has_receipt'])

        return expenses

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        expenses = context['expenses']

        total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or 0

        expense_breakdown = expenses.values('category__name').annotate(
            total_amount=Sum('amount'),
            count=Count('id')
        ).order_by('-total_amount')

        payment_breakdown = expenses.values('payment_method').annotate(
            total_amount=Sum('amount'),
            count=Count('id')
        ).order_by('-total_amount')

        context.update({
            'project': self.project,
            'filter_form': self.filter_form,
            'total_expenses': total_expenses,
            'expense_breakdown': expense_breakdown,
            'payment_breakdown': payment_breakdown,
            'expense_count': expenses.count(),
        })
        return context


class ExpenseCreateView(LoginRequiredMixin, generic.CreateView):
    """Create a new expense entry"""
    model = ExpenseEntry
    form_class = ExpenseEntryForm
    template_name = 'expenses/expense_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(
            Project, pk=kwargs['project_pk'], created_by=request.user
        )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.project = self.project
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Expense entry "{self.object.description}" added successfully!'
        )
        return response

    def get_success_url(self):
        return reverse('project_detail', kwargs={'pk': self.project.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.project
        context['action'] = 'Create'
        return context


class ExpenseUpdateView(LoginRequiredMixin, generic.UpdateView):
    """Update an existing expense entry"""
    model = ExpenseEntry
    form_class = ExpenseEntryForm
    template_name = 'expenses/expense_form.html'

    def get_queryset(self):
        return ExpenseEntry.objects.filter(project__created_by=self.request.user)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Expense entry "{self.object.description}" updated successfully!'
        )
        return response

    def get_success_url(self):
        return reverse('expense_list', kwargs={'project_pk': self.object.project.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project
        context['expense'] = self.object
        context['action'] = 'Update'
        return context


class ExpenseDeleteView(LoginRequiredMixin, generic.DeleteView):
    """Delete an expense entry"""
    model = ExpenseEntry
    template_name = 'expenses/expense_confirm_delete.html'
    context_object_name = 'expense'

    def get_queryset(self):
        return ExpenseEntry.objects.filter(project__created_by=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project
        return context

    def form_valid(self, form):
        project_pk = self.object.project.pk
        description = self.object.description
        self.object.delete()
        messages.success(self.request, f'Expense entry "{description}" deleted successfully!')
        return redirect('expense_list', project_pk=project_pk)


class ExpenseDetailView(LoginRequiredMixin, generic.DetailView):
    """View expense details including receipts"""
    model = ExpenseEntry
    template_name = 'expenses/expense_detail.html'
    context_object_name = 'expense'

    def get_queryset(self):
        return ExpenseEntry.objects.filter(project__created_by=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project
        context['receipts'] = self.object.receipts.all()
        return context


class ExpenseReceiptUploadView(LoginRequiredMixin, generic.CreateView):
    """Upload a receipt for an expense"""
    model = ExpenseReceipt
    form_class = ExpenseReceiptForm
    template_name = 'expenses/receipt_upload.html'

    def dispatch(self, request, *args, **kwargs):
        self.expense = get_object_or_404(
            ExpenseEntry, pk=kwargs['expense_pk'], project__created_by=request.user
        )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.expense = self.expense
        response = super().form_valid(form)

        # Update has_receipt flag
        self.expense.has_receipt = True
        self.expense.save()

        messages.success(self.request, 'Receipt uploaded successfully!')
        return response

    def get_success_url(self):
        return reverse('expense_detail', kwargs={'pk': self.expense.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['expense'] = self.expense
        context['project'] = self.expense.project
        return context


class ExpenseReceiptDeleteView(LoginRequiredMixin, generic.DeleteView):
    """Delete a receipt"""
    model = ExpenseReceipt
    template_name = 'expenses/receipt_confirm_delete.html'
    context_object_name = 'receipt'

    def get_queryset(self):
        return ExpenseReceipt.objects.filter(expense__project__created_by=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['expense'] = self.object.expense
        context['project'] = self.object.expense.project
        return context

    def form_valid(self, form):
        expense = self.object.expense
        self.object.delete()

        # Update has_receipt flag if no more receipts
        if not expense.receipts.exists():
            expense.has_receipt = False
            expense.save()

        messages.success(self.request, 'Receipt deleted successfully!')
        return redirect('expense_detail', pk=expense.pk)


class ExpenseCategoriesAPIView(LoginRequiredMixin, generic.View):
    """API endpoint to get expense categories (for AJAX)"""

    def get(self, request, *args, **kwargs):
        categories = ExpenseCategory.objects.all().values('id', 'name', 'key', 'description')
        return JsonResponse(list(categories), safe=False)


class ExpenseSummaryAPIView(LoginRequiredMixin, generic.View):
    """API endpoint to get expense summary for a project"""

    def get(self, request, project_pk, *args, **kwargs):
        project = get_object_or_404(Project, pk=project_pk, created_by=request.user)
        expenses = ExpenseEntry.objects.filter(project=project)

        total = expenses.aggregate(total=Sum('amount'))['total'] or 0
        count = expenses.count()

        by_category = list(expenses.values('category__name').annotate(
            total=Sum('amount')
        ).order_by('-total'))

        data = {
            'total': float(total),
            'count': count,
            'by_category': by_category
        }
        return JsonResponse(data)




