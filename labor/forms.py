from django import forms
from labor.models import LaborEntry
from django.core.exceptions import ValidationError


class LaborEntryForm(forms.ModelForm):
    """Form for creating and editing labor entries"""

    class Meta:
        model = LaborEntry
        fields = [
            'category',
            'work_date',
            'number_of_workers',
            'rate_per_worker_per_day',
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
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        workers = cleaned_data.get('number_of_workers')
        rate = cleaned_data.get('rate_per_worker_per_day')

        if workers and rate and rate <= 0:
            raise ValidationError('Daily rate must be greater than zero.')

        return cleaned_data


