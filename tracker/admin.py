from django.contrib import admin
from .models import *

# Register your models here.


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'company', 'phone', 'receive_email_alerts']
    list_filter = ['role', 'receive_email_alerts']
    search_fields = ['user__username', 'user__email', 'company', 'phone']


class TemplateMaterialInline(admin.TabularInline):
    model = TemplateMaterial
    extra = 1


@admin.register(ProjectTemplate)
class ProjectTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_by', 'is_public', 'created_at']
    list_filter = ['is_public', 'created_at']
    search_fields = ['name', 'description']
    inlines = [TemplateMaterialInline]


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'location', 'status', 'budget', 'total_spent', 'start_date', 'created_by']
    list_filter = ['status', 'created_at', 'created_from_template']
    search_fields = ['name', 'location', 'description']
    date_hierarchy = 'start_date'
    readonly_fields = ['created_at', 'updated_at', 'budget_alert_sent']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'location')
        }),
        ('Project Details', {
            'fields': ('budget', 'status', 'start_date', 'end_date')
        }),
        ('Template', {
            'fields': ('created_from_template',),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('created_by', 'budget_alert_sent', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(MaterialUnit)
class MaterialUnitAdmin(admin.ModelAdmin):
    list_display = ['name', 'abbreviation']
    search_fields = ['name', 'abbreviation']


@admin.register(MaterialEntry)
class MaterialEntryAdmin(admin.ModelAdmin):
    list_display = ['material_type', 'description', 'quantity', 'quantity_used', 'quantity_remaining', 
                    'unit', 'cost', 'project', 'purchase_date', 'has_receipt']
    list_filter = ['material_type', 'has_receipt', 'purchase_date']
    search_fields = ['description', 'supplier', 'project__name']
    date_hierarchy = 'purchase_date'
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Material Information', {
            'fields': ('project', 'material_type', 'description')
        }),
        ('Quantity and Usage', {
            'fields': ('quantity', 'quantity_used', 'unit')
        }),
        ('Cost', {
            'fields': ('cost',)
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
    list_display = ['material_entry', 'original_filename', 'file_size_mb', 'is_primary', 'uploaded_at']
    list_filter = ['is_primary', 'uploaded_at']
    search_fields = ['material_entry__description', 'original_filename', 'notes']
    date_hierarchy = 'uploaded_at'
    readonly_fields = ['uploaded_at', 'file_size']


@admin.register(ProjectPhoto)
class ProjectPhotoAdmin(admin.ModelAdmin):
    list_display = ['project', 'title', 'taken_date', 'uploaded_by', 'uploaded_at']
    list_filter = ['taken_date', 'uploaded_at']
    search_fields = ['project__name', 'title', 'description']
    date_hierarchy = 'uploaded_at'
    readonly_fields = ['uploaded_at']


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['project', 'action', 'user', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['project__name', 'description', 'user__username']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']
    
    def has_add_permission(self, request):
        # Activity logs are auto-created, not manually added
        return False


@admin.register(BudgetAlert)
class BudgetAlertAdmin(admin.ModelAdmin):
    list_display = ['project', 'alert_type', 'percentage', 'is_read', 'email_sent', 'created_at']
    list_filter = ['alert_type', 'is_read', 'email_sent', 'created_at']
    search_fields = ['project__name', 'message']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']
    
    actions = ['mark_as_read']
    
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
    mark_as_read.short_description = "Mark selected alerts as read"


