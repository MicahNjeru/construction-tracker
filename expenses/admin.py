from django.contrib import admin
from .models import ExpenseCategory, ExpenseEntry, ExpenseReceipt

# Register your models here.


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    """Admin interface for ExpenseCategory"""
    
    list_display = ['name', 'key', 'entry_count']
    list_filter = ['name']
    search_fields = ['name', 'key', 'description']
    prepopulated_fields = {'key': ('name',)}
    
    fieldsets = (
        (None, {
            'fields': ('name', 'key', 'description')
        }),
    )
    
    def entry_count(self, obj):
        """Count of expense entries in this category"""
        return obj.expense_entries.count()
    entry_count.short_description = 'Entries'


class ExpenseReceiptInline(admin.TabularInline):
    """Inline admin for expense receipts"""
    model = ExpenseReceipt
    extra = 0
    readonly_fields = ['uploaded_by', 'uploaded_at']
    fields = ['file', 'description', 'uploaded_by', 'uploaded_at']
    
    def has_add_permission(self, request, obj=None):
        return True


@admin.register(ExpenseEntry)
class ExpenseEntryAdmin(admin.ModelAdmin):
    """Admin interface for ExpenseEntry"""
    
    list_display = [
        'description', 
        'project', 
        'category', 
        'amount', 
        'expense_date',
        'payment_method',
        'has_receipt',
        'created_by'
    ]
    list_filter = [
        'category', 
        'payment_method', 
        'has_receipt', 
        'is_recurring',
        'expense_date',
        'created_at'
    ]
    search_fields = [
        'description', 
        'payee', 
        'reference_number', 
        'notes',
        'project__name'
    ]
    readonly_fields = ['created_by', 'created_at', 'updated_at', 'receipt_count']
    date_hierarchy = 'expense_date'
    inlines = [ExpenseReceiptInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'project',
                'category',
                'description',
                'amount',
                'expense_date'
            )
        }),
        ('Payment Details', {
            'fields': (
                'payment_method',
                'payee',
                'reference_number',
                'has_receipt',
                'is_recurring'
            )
        }),
        ('Additional Information', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': (
                'created_by',
                'created_at',
                'updated_at',
                'receipt_count'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Set created_by if creating new entry"""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('project', 'category', 'created_by')


@admin.register(ExpenseReceipt)
class ExpenseReceiptAdmin(admin.ModelAdmin):
    """Admin interface for ExpenseReceipt"""
    
    list_display = [
        'expense',
        'description',
        'file',
        'uploaded_by',
        'uploaded_at'
    ]
    list_filter = ['uploaded_at']
    search_fields = [
        'expense__description',
        'description',
        'expense__project__name'
    ]
    readonly_fields = ['uploaded_by', 'uploaded_at']
    date_hierarchy = 'uploaded_at'
    
    fieldsets = (
        (None, {
            'fields': ('expense', 'file', 'description')
        }),
        ('Metadata', {
            'fields': ('uploaded_by', 'uploaded_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Set uploaded_by if creating new receipt"""
        if not change:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('expense', 'expense__project', 'uploaded_by')


