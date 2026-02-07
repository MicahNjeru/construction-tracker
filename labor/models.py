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
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        ordering = ['-work_date', '-created_at']
        unique_together = ('project', 'category', 'work_date')
        verbose_name_plural = 'Labor Entries'


    def __str__(self):
        return f"{self.category.name} - {self.work_date}"


    @property
    def total_cost(self):
        """Total labor cost for this entry (computed)"""
        return self.number_of_workers * self.rate_per_worker_per_day


