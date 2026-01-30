from django.contrib import admin
from .models import Project, MaterialUnit, MaterialEntry, Receipt

# Register your models here.


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'location', 'status', 'budget', 'total_spent', 'start_date', 'created_by']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'location', 'description']
    date_hierarchy = 'start_date'
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'location')
        }),
        ('Project Details', {
            'fields': ('budget', 'status', 'start_date', 'end_date')
        }),
        ('System Information', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(MaterialUnit)
class MaterialUnitAdmin(admin.ModelAdmin):
    list_display = ['name', 'abbreviation']
    search_fields = ['name', 'abbreviation']


@admin.register(MaterialEntry)
class MaterialEntryAdmin(admin.ModelAdmin):
    list_display = ['material_type', 'description', 'quantity', 'unit', 'cost', 'project', 'purchase_date', 'has_receipt']
    list_filter = ['material_type', 'has_receipt', 'purchase_date']
    search_fields = ['description', 'supplier', 'project__name']
    date_hierarchy = 'purchase_date'
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Material Information', {
            'fields': ('project', 'material_type', 'description')
        }),
        ('Quantity and Cost', {
            'fields': ('quantity', 'unit', 'cost')
        }),
        ('Purchase Details', {
            'fields': ('purchase_date', 'supplier', 'notes', 'has_receipt')
        }),
        ('System Information', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ['material_entry', 'original_filename', 'file_size_mb', 'uploaded_at']
    search_fields = ['material_entry__description', 'original_filename']
    date_hierarchy = 'uploaded_at'
    readonly_fields = ['uploaded_at', 'file_size']