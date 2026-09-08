from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Sum, Count, F
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.views import generic
from tracker.models import Project
from labor.models import LaborEntry, LaborReceipt
from .forms import LaborEntryForm

# Create your views here.


class LaborCreateView(LoginRequiredMixin, generic.CreateView):
    model = LaborEntry
    form_class = LaborEntryForm
    template_name = 'labor/labor_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(Project, pk=kwargs['project_pk'])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.project = self.project
        form.instance.created_by = self.request.user
        response = super().form_valid(form)

        receipt_file = self.request.FILES.get('receipt_file')
        if receipt_file:
            LaborReceipt.objects.create(
                labor_entry=self.object,
                file=receipt_file,
                description=self.request.POST.get('receipt_description', ''),
                uploaded_by=self.request.user
            )
            self.object.has_receipt = True
            self.object.save(update_fields=['has_receipt'])

        messages.success(self.request, 'Labor entry added successfully!')
        return response

    def get_success_url(self):
        return reverse('project_detail', kwargs={'pk': self.project.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.project
        context['title'] = 'Add Labor Entry'
        return context


class LaborUpdateView(LoginRequiredMixin, generic.UpdateView):
    model = LaborEntry
    form_class = LaborEntryForm
    template_name = 'labor/labor_form.html'
    context_object_name = 'labor'

    def form_valid(self, form):
        response = super().form_valid(form)

        receipt_file = self.request.FILES.get('receipt_file')
        if receipt_file:
            LaborReceipt.objects.create(
                labor_entry=self.object,
                file=receipt_file,
                description=self.request.POST.get('receipt_description', ''),
                uploaded_by=self.request.user
            )
            self.object.has_receipt = True
            self.object.save(update_fields=['has_receipt'])

        messages.success(self.request, 'Labor entry updated successfully!')
        return response

    def get_success_url(self):
        return reverse('project_detail', kwargs={'pk': self.object.project.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project
        context['title'] = 'Edit Labor Entry'
        return context


class LaborDeleteView(LoginRequiredMixin, generic.DeleteView):
    model = LaborEntry
    template_name = 'labor/labor_confirm_delete.html'
    context_object_name = 'labor'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project
        return context

    def form_valid(self, form):
        project = self.object.project
        self.object.delete()
        messages.success(self.request, 'Labor entry deleted successfully!')
        return redirect('project_detail', pk=project.pk)


class LaborSummaryView(LoginRequiredMixin, generic.TemplateView):
    template_name = 'labor/labor_summary.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = get_object_or_404(Project, pk=self.kwargs['project_pk'])

        breakdown = project.labor_entries.values('category__name').annotate(
            total_cost=Sum(F('number_of_workers') * F('rate_per_worker_per_day') * F('number_of_days')),
            days=Count('id')
        ).order_by('-total_cost')

        context.update({
            'project': project,
            'labor_entries': project.labor_entries.all(),
            'labor_breakdown': breakdown,
            'total_labor_cost': project.total_labor_cost,
        })
        return context

