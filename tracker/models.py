from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
import os

# Create your models here.


class Project(models.Model):
    """Construction/Building Project model."""
    
    STATUS_CHOICES = [
        ('planning', 'Planning'),
        ('in_progress', 'In Progress'),
        ('on_hold', 'On Hold'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=300, blank=True)
    budget = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total project budget"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planning')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return self.name
    
    @property
    def total_spent(self):
        """Calculate total amount spent on materials."""
        total = self.material_entries.aggregate(
            total=models.Sum('cost')
        )['total']
        return total or Decimal('0.00')
    
    @property
    def remaining_budget(self):
        """Calculate remaining budget."""
        return self.budget - self.total_spent
    
    @property
    def budget_utilization_percentage(self):
        """Calculate budget utilization percentage."""
        if self.budget == 0:
            return 0
        return (self.total_spent / self.budget) * 100
    
    @property
    def material_count(self):
        """Count of material entries."""
        return self.material_entries.count()
    
    @property
    def is_over_budget(self):
        """Check if project is over budget."""
        return self.total_spent > self.budget
    
    @property
    def days_duration(self):
        """Calculate project duration in days."""
        if self.end_date and self.start_date:
            return (self.end_date - self.start_date).days
        return None


class MaterialUnit(models.Model):
    """Units of measurement for materials."""
    
    name = models.CharField(max_length=50, unique=True)
    abbreviation = models.CharField(max_length=10)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.abbreviation})"


class MaterialEntry(models.Model):
    """Material purchase/acquisition entry for a project."""
    
    MATERIAL_TYPES = [
        ('wood', 'Wood'),
        ('metal', 'Metal'),
        ('stones', 'Stones'),
        ('cement', 'Cement'),
        ('sand', 'Sand'),
        ('gravel', 'Gravel'),
        ('bricks', 'Bricks'),
        ('tiles', 'Tiles'),
        ('paint', 'Paint'),
        ('electrical', 'Electrical'),
        ('plumbing', 'Plumbing'),
        ('glass', 'Glass'),
        ('roofing', 'Roofing'),
        ('insulation', 'Insulation'),
        ('hardware', 'Hardware'),
        ('tools', 'Tools'),
        ('other', 'Other'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='material_entries')
    material_type = models.CharField(max_length=50, choices=MATERIAL_TYPES)
    description = models.CharField(max_length=300, help_text="Brief description of the material")
    quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    unit = models.ForeignKey(MaterialUnit, on_delete=models.PROTECT)
    cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    purchase_date = models.DateField()
    supplier = models.CharField(max_length=200, blank=True, help_text="Where/who you got it from")
    notes = models.TextField(blank=True)
    has_receipt = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-purchase_date', '-created_at']
        verbose_name_plural = 'Material entries'
    
    def __str__(self):
        return f"{self.get_material_type_display()} - {self.description[:50]}"
    
    @property
    def unit_cost(self):
        """Calculate cost per unit."""
        if self.quantity > 0:
            return self.cost / self.quantity
        return Decimal('0.00')
    
    @property
    def receipt_count(self):
        """Count of receipts for this material."""
        return self.receipts.count()


class Receipt(models.Model):
    """Receipt attachment for material entries"""
    
    material_entry = models.ForeignKey(
        MaterialEntry, 
        on_delete=models.CASCADE, 
        related_name='receipts'  # Changed from 'receipt' to 'receipts'
    )
    file = models.FileField(upload_to='receipts/%Y/%m/%d/')
    original_filename = models.CharField(max_length=255)
    file_size = models.IntegerField(help_text="File size in bytes")
    is_primary = models.BooleanField(default=False, help_text="Mark as primary receipt")
    notes = models.TextField(blank=True, help_text="Notes about this receipt")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-is_primary', '-uploaded_at']
    
    def __str__(self):
        primary = " (Primary)" if self.is_primary else ""
        return f"Receipt for {self.material_entry}{primary}"
    
    @property
    def file_extension(self):
        """Get file extension."""
        return os.path.splitext(self.original_filename)[1].lower()
    
    @property
    def is_image(self):
        """Check if file is an image."""
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        return self.file_extension in image_extensions
    
    @property
    def is_pdf(self):
        """Check if file is a PDF."""
        return self.file_extension == '.pdf'
    
    @property
    def file_size_mb(self):
        """Get file size in MB."""
        return round(self.file_size / (1024 * 1024), 2)
    
    def save(self, *args, **kwargs):
        """Auto-set as primary if it's the first receipt."""
        if not self.pk:  # New receipt
            if not self.material_entry.receipts.exists():
                self.is_primary = True
            # If marking as primary, unmark others
            if self.is_primary:
                self.material_entry.receipts.update(is_primary=False)
        super().save(*args, **kwargs)
        
        # Update material entry has_receipt flag
        self.material_entry.has_receipt = self.material_entry.receipts.exists()
        self.material_entry.save(update_fields=['has_receipt'])
    
    def delete(self, *args, **kwargs):
        """Delete file when receipt is deleted and update material entry."""
        material_entry = self.material_entry
        if self.file:
            if os.path.isfile(self.file.path):
                os.remove(self.file.path)
        
        super().delete(*args, **kwargs)
        
        # Update material entry has_receipt flag
        material_entry.has_receipt = material_entry.receipts.exists()
        material_entry.save(update_fields=['has_receipt'])
        
        # If deleted receipt was primary, make another one primary
        if self.is_primary and material_entry.receipts.exists():
            material_entry.receipts.first().save()  # Triggers the auto-primary logic


