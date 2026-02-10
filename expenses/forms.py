from django import forms
from .models import ExpenseEntry, ExpenseReceipt


class ExpenseEntryForm(forms.ModelForm):
    """Form for creating/editing expense entries"""
    
    class Meta:
        model = ExpenseEntry
        fields = [
            'category', 
            'description', 
            'amount', 
            'expense_date',
            'payment_method',
            'payee',
            'reference_number',
            'is_recurring',
            'has_receipt',
            'notes'
        ]
        widgets = {
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Transport of cement from supplier to site'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01'
            }),
            'expense_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'payment_method': forms.Select(attrs={
                'class': 'form-select'
            }),
            'payee': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., ABC Transport Services'
            }),
            'reference_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., TRX123456, License #2024-001'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional notes or details...'
            }),
            'has_receipt': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_recurring': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        help_texts = {
            'description': 'Provide a clear description of what this expense covers',
            'amount': 'Enter the total amount in Kenyan Shillings (Ksh)',
            'expense_date': 'Date when the expense was incurred',
            'reference_number': 'Transaction ID, receipt number, or any reference identifier',
        }


class ExpenseReceiptForm(forms.ModelForm):
    """Form for uploading expense receipts"""
    
    class Meta:
        model = ExpenseReceipt
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


class ExpenseFilterForm(forms.Form):
    """Form for filtering expense entries"""
    
    category = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    payment_method = forms.ChoiceField(
        choices=[('', 'All Payment Methods')] + ExpenseEntry.PAYMENT_METHOD_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
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
    
    has_receipt = forms.NullBooleanField(
        required=False,
        widget=forms.Select(
            choices=[
                ('', 'All'),
                ('true', 'With Receipt'),
                ('false', 'Without Receipt')
            ],
            attrs={'class': 'form-select'}
        )
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import ExpenseCategory
        self.fields['category'].queryset = ExpenseCategory.objects.all()


