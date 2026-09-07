from django import forms
from labor.models import LaborEntry, LaborReceipt
from django.core.exceptions import ValidationError


class LaborEntryForm(forms.ModelForm):
    class Meta:
        model = LaborEntry
        fields = [
            'category',
            'work_date',
            'number_of_workers',
            'rate_per_worker_per_day',
            'number_of_days',
            'notes'
        ]
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'work_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'number_of_workers': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'rate_per_worker_per_day': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'number_of_days': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2
            }),
        }


class LaborReceiptForm(forms.ModelForm):
    class Meta:
        model = LaborReceipt
        fields = ['file', 'description']
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*,application/pdf'
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional: Describe this receipt'
            }),
        }

