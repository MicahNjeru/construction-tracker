from django import forms
from .models import Project, MaterialEntry, Receipt
from django.core.exceptions import ValidationError


class ProjectForm(forms.ModelForm):
    """Form for creating and editing projects."""
    
    class Meta:
        model = Project
        fields = ['name', 'description', 'location', 'budget', 'status', 'start_date', 'end_date']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Smith Residence Renovation'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Brief description of the project'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Project location/address'
            }),
            'budget': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '0.00'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and end_date < start_date:
            raise ValidationError('End date cannot be before start date.')
        
        return cleaned_data


class MaterialEntryForm(forms.ModelForm):
    """Form for creating and editing material entries."""
    
    class Meta:
        model = MaterialEntry
        fields = ['material_type', 'description', 'quantity', 'unit', 'cost', 
                  'purchase_date', 'supplier', 'notes']
        widgets = {
            'material_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 2x4 lumber, 8ft length'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '0.00'
            }),
            'unit': forms.Select(attrs={
                'class': 'form-select'
            }),
            'cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '0.00'
            }),
            'purchase_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'supplier': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Home Depot, John\'s Hardware'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional notes (optional)'
            }),
        }


class ReceiptUploadForm(forms.ModelForm):
    """Form for uploading receipts."""
    
    class Meta:
        model = Receipt
        fields = ['file']
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*,.pdf'
            })
        }
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        
        if file:
            # Check file size (max 10MB)
            if file.size > 10 * 1024 * 1024:
                raise ValidationError('File size cannot exceed 10MB.')
            
            # Check file extension
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.pdf']
            ext = file.name.lower().split('.')[-1]
            if f'.{ext}' not in valid_extensions:
                raise ValidationError(
                    'Invalid file type. Allowed types: JPG, JPEG, PNG, GIF, WEBP, PDF'
                )
        
        return file
    
    def save(self, commit=True):
        receipt = super().save(commit=False)
        if self.cleaned_data.get('file'):
            receipt.original_filename = self.cleaned_data['file'].name
            receipt.file_size = self.cleaned_data['file'].size
        if commit:
            receipt.save()
        return receipt