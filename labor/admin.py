from django.contrib import admin
from labor.models import LaborCategory, LaborEntry

# Register your models here.


@admin.register(LaborCategory)
class LaborCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'key']
    search_fields = ['name', 'key']


@admin.register(LaborEntry)
class LaborEntryAdmin(admin.ModelAdmin):
    list_display = [
        'project',
        'category',
        'work_date',
        'number_of_workers',
        'rate_per_worker_per_day',
        'total_cost'
    ]
    list_filter = ['category', 'work_date']
    search_fields = ['project__name', 'category__name']
    date_hierarchy = 'work_date'
    readonly_fields = ['created_at', 'updated_at', 'total_cost']

    fieldsets = (
        ('Labor Details', {
            'fields': ('project', 'category', 'work_date')
        }),
        ('Costing', {
            'fields': ('number_of_workers', 'rate_per_worker_per_day')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('System Information', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )



