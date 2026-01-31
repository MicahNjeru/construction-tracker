from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import os

# Create your models here.


class UserProfile(models.Model):
    """Extended user profile with role and preferences."""
    
    ROLE_CHOICES = [
        ('owner', 'Project Owner'),
        ('manager', 'Project Manager'),
        ('worker', 'Worker'),
        ('viewer', 'Viewer'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='owner')
    phone = models.CharField(max_length=20, blank=True)
    company = models.CharField(max_length=200, blank=True)
    receive_email_alerts = models.BooleanField(default=True)
    budget_alert_threshold = models.IntegerField(
        default=90,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Send alert when budget utilization reaches this percentage"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"


class ProjectTemplate(models.Model):
    """Template for creating new projects with predefined materials."""
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    is_public = models.BooleanField(default=False, help_text="Make available to all users")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name


class TemplateMaterial(models.Model):
    """Pre-defined material for a project template."""
    
    template = models.ForeignKey(ProjectTemplate, on_delete=models.CASCADE, related_name='materials')
    material_type = models.CharField(max_length=50)
    description = models.CharField(max_length=300)
    estimated_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_name = models.CharField(max_length=50)
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.material_type} - {self.description}"


class Project(models.Model):
    """Construction/Building Project model"""
    
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
    created_from_template = models.ForeignKey(
        ProjectTemplate, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Template used to create this project"
    )
    budget_alert_sent = models.BooleanField(default=False)
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
    
    @property
    def photo_count(self):
        """Count of project photos."""
        return self.photos.count()
    
    def needs_budget_alert(self, threshold=90):
        """Check if budget alert should be sent."""
        return (
            not self.budget_alert_sent and 
            self.budget_utilization_percentage >= threshold
        )


class MaterialUnit(models.Model):
    """Units of measurement for materials."""
    
    name = models.CharField(max_length=50, unique=True)
    abbreviation = models.CharField(max_length=10)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.abbreviation})"


class MaterialEntry(models.Model):
    """Material purchase/acquisition entry for a project"""
    
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
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Total quantity purchased"
    )
    quantity_used = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Quantity already used"
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
    
    @property
    def quantity_remaining(self):
        """Calculate remaining quantity."""
        return self.quantity - self.quantity_used
    
    @property
    def usage_percentage(self):
        """Calculate usage percentage."""
        if self.quantity > 0:
            return (self.quantity_used / self.quantity) * 100
        return 0
    
    @property
    def is_depleted(self):
        """Check if material is fully used."""
        return self.quantity_used >= self.quantity


class Receipt(models.Model):
    """Receipt attachment for material entries."""
    
    material_entry = models.ForeignKey(
        MaterialEntry, 
        on_delete=models.CASCADE, 
        related_name='receipts'
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
        if not self.pk:
            if not self.material_entry.receipts.exists():
                self.is_primary = True
            if self.is_primary:
                self.material_entry.receipts.update(is_primary=False)
        super().save(*args, **kwargs)
        
        self.material_entry.has_receipt = self.material_entry.receipts.exists()
        self.material_entry.save(update_fields=['has_receipt'])
    
    def delete(self, *args, **kwargs):
        """Delete file when receipt is deleted and update material entry."""
        material_entry = self.material_entry
        if self.file:
            if os.path.isfile(self.file.path):
                os.remove(self.file.path)
        
        super().delete(*args, **kwargs)
        
        material_entry.has_receipt = material_entry.receipts.exists()
        material_entry.save(update_fields=['has_receipt'])
        
        if self.is_primary and material_entry.receipts.exists():
            material_entry.receipts.first().save()


class ProjectPhoto(models.Model):
    """Photo gallery for tracking project progress"""
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='photos')
    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    photo = models.ImageField(upload_to='project_photos/%Y/%m/%d/')
    taken_date = models.DateField(null=True, blank=True, help_text="When the photo was taken")
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-taken_date', '-uploaded_at']
    
    def __str__(self):
        return f"Photo for {self.project.name} - {self.uploaded_at.date()}"
    
    def delete(self, *args, **kwargs):
        """Delete photo file when deleted."""
        if self.photo:
            if os.path.isfile(self.photo.path):
                os.remove(self.photo.path)
        super().delete(*args, **kwargs)


class ActivityLog(models.Model):
    """Activity log for tracking project changes"""
    
    ACTION_CHOICES = [
        ('project_created', 'Project Created'),
        ('project_updated', 'Project Updated'),
        ('material_added', 'Material Added'),
        ('material_updated', 'Material Updated'),
        ('material_deleted', 'Material Deleted'),
        ('material_used', 'Material Usage Updated'),
        ('receipt_uploaded', 'Receipt Uploaded'),
        ('receipt_deleted', 'Receipt Deleted'),
        ('photo_uploaded', 'Photo Uploaded'),
        ('photo_deleted', 'Photo Deleted'),
        ('budget_alert', 'Budget Alert Triggered'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='activity_logs')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    description = models.TextField()
    related_material = models.ForeignKey(
        MaterialEntry, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_action_display()} - {self.project.name}"


class BudgetAlert(models.Model):
    """Budget alert notifications"""
    
    ALERT_TYPE_CHOICES = [
        ('warning', 'Warning (75%)'),
        ('critical', 'Critical (90%)'),
        ('exceeded', 'Budget Exceeded'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='budget_alerts')
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPE_CHOICES)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_alert_type_display()} - {self.project.name}"


