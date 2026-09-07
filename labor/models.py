from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from tracker.models import Project

# Create your models here.


class LaborCategory(models.Model):
    """Database-driven labor roles/categories"""

    key = models.SlugField(max_length=50, unique=True, help_text="Machine-readable key, e.g. 'mason', 'carpenter'")
    name = models.CharField(max_length=100, help_text="Human-readable name, e.g. 'Mason'")

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Labor Categories'

    def __str__(self):
        return self.name


class LaborEntry(models.Model):
    """Daily labor cost entry for a project and role"""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='labor_entries')
    category = models.ForeignKey(LaborCategory, on_delete=models.PROTECT, related_name='labor_entries')
    work_date = models.DateField()
    number_of_workers = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    rate_per_worker_per_day = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    number_of_days = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)], help_text="Number of days worked at this rate")
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        ordering = ['-work_date', '-created_at']
        unique_together = ('project', 'category', 'work_date', 'created_at')
        verbose_name_plural = 'Labor Entries'


    def __str__(self):
        return f"{self.category.name} - {self.work_date}"


    @property
    def total_cost(self):
        """Total labor cost for this entry (computed)"""
        return self.number_of_workers * self.rate_per_worker_per_day * self.number_of_days
    @property
    def receipt_count(self):
        return self.receipts.count()


class LaborReceipt(models.Model):
    """Receipt/proof of payment for a labor entry"""

    labor_entry = models.ForeignKey(LaborEntry, on_delete=models.CASCADE, related_name='receipts')
    file = models.FileField(upload_to='receipts/labor/%Y/%m/')
    description = models.CharField(max_length=200, blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name_plural = 'Labor Receipts'

    def __str__(self):
        return f"Receipt for {self.labor_entry}"


