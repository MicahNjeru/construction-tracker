from django import forms
from django.db.models import Q
from .models import Project, MaterialEntry, Receipt, ProjectTemplate, TemplateMaterial, ProjectPhoto, UserProfile
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
    """Form for creating and editing material entries"""
    
    class Meta:
        model = MaterialEntry
        fields = ['material_type', 'description', 'quantity', 'quantity_used', 'unit', 'cost', 
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
            'quantity_used': forms.NumberInput(attrs={
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
    
    def clean(self):
        cleaned_data = super().clean()
        quantity = cleaned_data.get('quantity')
        quantity_used = cleaned_data.get('quantity_used')
        
        if quantity and quantity_used and quantity_used > quantity:
            raise ValidationError('Quantity used cannot exceed total quantity.')
        
        return cleaned_data


class MaterialUsageForm(forms.Form):
    """Quick form for updating material usage."""
    
    quantity_used = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': 'Enter quantity used'
        })
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Notes about this usage (optional)'
        })
    )


class ReceiptUploadForm(forms.ModelForm):
    """Form for uploading receipts."""
    
    class Meta:
        model = Receipt
        fields = ['file', 'is_primary', 'notes']
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*,.pdf'
            }),
            'is_primary': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Notes about this receipt (optional)'
            }),
        }
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        
        if file:
            if file.size > 10 * 1024 * 1024:
                raise ValidationError('File size cannot exceed 10MB.')
            
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


class ProjectTemplateForm(forms.ModelForm):
    """Form for creating project templates."""
    
    class Meta:
        model = ProjectTemplate
        fields = ['name', 'description', 'is_public']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Standard Home Renovation'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe this template'
            }),
            'is_public': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class TemplateMaterialForm(forms.ModelForm):
    """Form for adding materials to templates."""
    
    class Meta:
        model = TemplateMaterial
        fields = ['material_type', 'description', 'estimated_quantity', 'unit_name', 
                  'estimated_cost', 'notes']
        widgets = {
            'material_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Material description'
            }),
            'estimated_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'unit_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., bags, kg, pieces'
            }),
            'estimated_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2
            }),
        }


class CreateProjectFromTemplateForm(forms.Form):
    """Form for creating a project from a template."""
    
    template = forms.ModelChoiceField(
        queryset=ProjectTemplate.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Select a template to start with"
    )
    
    name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'New project name'
        })
    )
    
    location = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Project location'
        })
    )
    
    budget = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': '0.00'
        })
    )
    
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            # Show user's templates and public templates
            self.fields['template'].queryset = ProjectTemplate.objects.filter(
                Q(created_by=user) | Q(is_public=True)
            )


class ProjectPhotoForm(forms.ModelForm):
    """Form for uploading project photos."""
    
    class Meta:
        model = ProjectPhoto
        fields = ['title', 'description', 'photo', 'taken_date']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Photo title (optional)'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Photo description (optional)'
            }),
            'photo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'taken_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }
    
    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        
        if photo:
            if photo.size > 10 * 1024 * 1024:
                raise ValidationError('Image size cannot exceed 10MB.')
            
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            ext = photo.name.lower().split('.')[-1]
            if f'.{ext}' not in valid_extensions:
                raise ValidationError(
                    'Invalid file type. Allowed types: JPG, JPEG, PNG, GIF, WEBP'
                )
        
        return photo


class UserProfileForm(forms.ModelForm):
    """Form for updating user profile and preferences."""
    
    class Meta:
        model = UserProfile
        fields = ['phone', 'company', 'receive_email_alerts', 'budget_alert_threshold']
        widgets = {
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+1234567890'
            }),
            'company': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Company name'
            }),
            'receive_email_alerts': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'budget_alert_threshold': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '100',
                'step': '5'
            }),
        }


class MaterialSearchForm(forms.Form):
    """Form for searching and filtering materials."""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search materials...'
        })
    )
    
    material_type = forms.ChoiceField(
        required=False,
        choices=[('', 'All Types')] + MaterialEntry.MATERIAL_TYPES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    usage_status = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All'),
            ('available', 'Available'),
            ('depleted', 'Depleted'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )


