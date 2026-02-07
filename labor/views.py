from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, F
from django.shortcuts import render, redirect, get_object_or_404
from tracker.models import Project
from labor.models import LaborEntry, LaborCategory
from .forms import LaborEntryForm

# Create your views here.


@login_required
def labor_create(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)

    if request.method == 'POST':
        form = LaborEntryForm(request.POST)
        if form.is_valid():
            labor = form.save(commit=False)
            labor.project = project
            labor.created_by = request.user
            labor.save()
            messages.success(request, 'Labor entry added successfully!')
            return redirect('project_detail', pk=project.pk)
    else:
        form = LaborEntryForm()

    return render(request, 'labor/labor_form.html', {
        'form': form,
        'project': project,
        'title': 'Add Labor Entry'
    })

@login_required
def labor_update(request, pk):
    labor = get_object_or_404(LaborEntry, pk=pk)
    project = labor.project

    if request.method == 'POST':
        form = LaborEntryForm(request.POST, instance=labor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Labor entry updated successfully!')
            return redirect('project_detail', pk=project.pk)
    else:
        form = LaborEntryForm(instance=labor)

    return render(request, 'labor/labor_form.html', {
        'form': form,
        'project': project,
        'title': 'Update Labor Entry',
        'labor': labor
    })


@login_required
def labor_delete(request, pk):
    labor = get_object_or_404(LaborEntry, pk=pk)
    project = labor.project

    if request.method == 'POST':
        labor.delete()
        messages.success(request, 'Labor entry deleted successfully!')
        return redirect('project_detail', pk=project.pk)

    return render(request, 'labor/labor_confirm_delete.html', {
        'labor': labor,
        'project': project
    })


@login_required
def labor_summary(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)

    breakdown = project.labor_entries.values('category__name').annotate(
        total_cost=Sum(F('number_of_workers') * F('rate_per_worker_per_day')),
        days=Count('id')
    ).order_by('-total_cost')

    context = {
        'project': project,
        'labor_entries': project.labor_entries.all(),
        'labor_breakdown': breakdown,
        'total_labor_cost': project.total_labor_cost,
    }

    return render(request, 'labor/labor_summary.html', context)


