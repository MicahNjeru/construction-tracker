from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
from tracker.models import Project

# Create your models here.


class ExpenseCategory(models.Model):
    """Database-driven expense categories"""

    key = models.SlugField(max_length=50, unique=True, help_text="Machine-readable key, e.g. 'transport', 'licenses'")
    name = models.CharField(max_length=100, help_text="Human-readable name, e.g. 'Material Transport'")
    description = models.TextField(blank=True, help_text="Optional description of what this category covers")

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Expense Categories'

    def __str__(self):
        return self.name


class ExpenseEntry(models.Model):
    """Miscellaneous expense entry for a project"""
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('mpesa', 'M-Pesa'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('card', 'Card'),
        ('other', 'Other'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='expense_entries')
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT, related_name='expense_entries')
    description = models.CharField(max_length=300, help_text="Brief description of the expense")
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total amount spent"
    )
    expense_date = models.DateField(help_text="Date when expense was incurred")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cash')
    payee = models.CharField(max_length=200, blank=True, help_text="Who was paid (vendor, government office, etc.)")
    reference_number = models.CharField(max_length=100, blank=True, help_text="Transaction reference, receipt number, or invoice number")
    notes = models.TextField(blank=True)
    has_receipt = models.BooleanField(default=False)
    is_recurring = models.BooleanField(default=False, help_text="Is this a recurring expense?")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-expense_date', '-created_at']
        verbose_name_plural = 'Expense Entries'
    
    def __str__(self):
        return f"{self.category.name} - {self.description[:50]} (Ksh{self.amount})"
    
    @property
    def receipt_count(self):
        """Count of receipts for this expense."""
        return self.receipts.count()


class ExpenseReceipt(models.Model):
    """Receipt/proof of payment for an expense"""
    
    expense = models.ForeignKey(ExpenseEntry, on_delete=models.CASCADE, related_name='receipts')
    file = models.FileField(upload_to='receipts/expenses/%Y/%m/')
    description = models.CharField(max_length=200, blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-uploaded_at']
        verbose_name_plural = 'Expense Receipts'
    
    def __str__(self):
        return f"Receipt for {self.expense}"


