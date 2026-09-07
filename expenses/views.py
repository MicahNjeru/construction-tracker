from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.http import JsonResponse
from tracker.models import Project
from .models import ExpenseEntry, ExpenseReceipt, ExpenseCategory
from .forms import ExpenseEntryForm, ExpenseReceiptForm, ExpenseFilterForm

# Create your views here.


@login_required
def expense_list(request, project_pk):
    """List all expenses for a project with filtering"""
    project = get_object_or_404(Project, pk=project_pk, created_by=request.user)
    
    # Get all expenses for this project
    expenses = ExpenseEntry.objects.filter(project=project).select_related(
        'category', 'created_by'
    )
    
    # Apply filters
    filter_form = ExpenseFilterForm(request.GET)
    if filter_form.is_valid():
        if filter_form.cleaned_data.get('category'):
            expenses = expenses.filter(category=filter_form.cleaned_data['category'])
        
        if filter_form.cleaned_data.get('payment_method'):
            expenses = expenses.filter(payment_method=filter_form.cleaned_data['payment_method'])
        
        if filter_form.cleaned_data.get('date_from'):
            expenses = expenses.filter(expense_date__gte=filter_form.cleaned_data['date_from'])
        
        if filter_form.cleaned_data.get('date_to'):
            expenses = expenses.filter(expense_date__lte=filter_form.cleaned_data['date_to'])
        
        if filter_form.cleaned_data.get('has_receipt') is not None:
            expenses = expenses.filter(has_receipt=filter_form.cleaned_data['has_receipt'])
    
    # Calculate totals
    total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or 0
    
    # Breakdown by category
    expense_breakdown = expenses.values(
        'category__name'
    ).annotate(
        total_amount=Sum('amount'),
        count=Count('id')
    ).order_by('-total_amount')
    
    # Breakdown by payment method
    payment_breakdown = expenses.values(
        'payment_method'
    ).annotate(
        total_amount=Sum('amount'),
        count=Count('id')
    ).order_by('-total_amount')
    
    context = {
        'project': project,
        'expenses': expenses,
        'filter_form': filter_form,
        'total_expenses': total_expenses,
        'expense_breakdown': expense_breakdown,
        'payment_breakdown': payment_breakdown,
        'expense_count': expenses.count(),
    }
    
    return render(request, 'expenses/expense_list.html', context)


@login_required
def expense_create(request, project_pk):
    """Create a new expense entry"""
    project = get_object_or_404(Project, pk=project_pk, created_by=request.user)
    
    if request.method == 'POST':
        form = ExpenseEntryForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.project = project
            expense.created_by = request.user
            expense.save()
            
            messages.success(
                request, 
                f'Expense entry "{expense.description}" added successfully!'
            )
            return redirect('project_detail', pk=project.pk)
    else:
        form = ExpenseEntryForm()
    
    context = {
        'project': project,
        'form': form,
        'action': 'Create'
    }
    
    return render(request, 'expenses/expense_form.html', context)


@login_required
def expense_update(request, pk):
    """Update an existing expense entry"""
    expense = get_object_or_404(
        ExpenseEntry, 
        pk=pk, 
        project__created_by=request.user
    )
    
    if request.method == 'POST':
        form = ExpenseEntryForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            messages.success(
                request, 
                f'Expense entry "{expense.description}" updated successfully!'
            )
            return redirect('expense_list', project_pk=expense.project.pk)
    else:
        form = ExpenseEntryForm(instance=expense)
    
    context = {
        'project': expense.project,
        'form': form,
        'expense': expense,
        'action': 'Update'
    }
    
    return render(request, 'expenses/expense_form.html', context)


@login_required
def expense_delete(request, pk):
    """Delete an expense entry"""
    expense = get_object_or_404(
        ExpenseEntry, 
        pk=pk, 
        project__created_by=request.user
    )
    project_pk = expense.project.pk
    
    if request.method == 'POST':
        description = expense.description
        expense.delete()
        messages.success(
            request, 
            f'Expense entry "{description}" deleted successfully!'
        )
        return redirect('expense_list', project_pk=project_pk)
    
    context = {
        'expense': expense,
        'project': expense.project
    }
    
    return render(request, 'expenses/expense_confirm_delete.html', context)


@login_required
def expense_detail(request, pk):
    """View expense details including receipts"""
    expense = get_object_or_404(
        ExpenseEntry, 
        pk=pk, 
        project__created_by=request.user
    )
    
    receipts = expense.receipts.all()
    
    context = {
        'expense': expense,
        'project': expense.project,
        'receipts': receipts
    }
    
    return render(request, 'expenses/expense_detail.html', context)


@login_required
def expense_receipt_upload(request, expense_pk):
    """Upload a receipt for an expense"""
    expense = get_object_or_404(
        ExpenseEntry, 
        pk=expense_pk, 
        project__created_by=request.user
    )
    
    if request.method == 'POST':
        form = ExpenseReceiptForm(request.POST, request.FILES)
        if form.is_valid():
            receipt = form.save(commit=False)
            receipt.expense = expense
            receipt.uploaded_by = request.user
            receipt.save()
            
            # Update has_receipt flag
            expense.has_receipt = True
            expense.save()
            
            messages.success(request, 'Receipt uploaded successfully!')
            return redirect('expense_detail', pk=expense.pk)
    else:
        form = ExpenseReceiptForm()
    
    context = {
        'expense': expense,
        'project': expense.project,
        'form': form
    }
    
    return render(request, 'expenses/receipt_upload.html', context)


@login_required
def expense_receipt_delete(request, pk):
    """Delete a receipt"""
    receipt = get_object_or_404(
        ExpenseReceipt, 
        pk=pk, 
        expense__project__created_by=request.user
    )
    expense = receipt.expense
    
    if request.method == 'POST':
        receipt.delete()
        
        # Update has_receipt flag if no more receipts
        if not expense.receipts.exists():
            expense.has_receipt = False
            expense.save()
        
        messages.success(request, 'Receipt deleted successfully!')
        return redirect('expense_detail', pk=expense.pk)
    
    context = {
        'receipt': receipt,
        'expense': expense,
        'project': expense.project
    }
    
    return render(request, 'expenses/receipt_confirm_delete.html', context)


@login_required
def expense_api_categories(request):
    """API endpoint to get expense categories (for AJAX)"""
    categories = ExpenseCategory.objects.all().values('id', 'name', 'key', 'description')
    return JsonResponse(list(categories), safe=False)


@login_required
def expense_api_summary(request, project_pk):
    """API endpoint to get expense summary for a project"""
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

