import os
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from expenses.models import ExpenseCategory


class Command(BaseCommand):
    help = 'Load expense categories from a txt file, Excel file (.xlsx, .xls), or create defaults'

    def add_arguments(self, parser):
        parser.add_argument(
            'file',
            nargs='?',
            type=str,
            help='Path to file containing expense categories (txt, xlsx, or xls)',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing categories before loading',
        )

    def handle(self, *args, **options):
        file_path = options.get('file')
        clear_existing = options.get('clear', False)

        # Clear existing categories if requested
        if clear_existing:
            count = ExpenseCategory.objects.count()
            ExpenseCategory.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(f'Cleared {count} existing expense categories')
            )

        if file_path:
            # Load from file
            if not os.path.exists(file_path):
                raise CommandError(f'File "{file_path}" does not exist')

            file_extension = os.path.splitext(file_path)[1].lower()

            if file_extension == '.txt':
                self.load_from_txt(file_path)
            elif file_extension in ['.xlsx', '.xls']:
                self.load_from_excel(file_path)
            else:
                raise CommandError(
                    f'Unsupported file format: {file_extension}. '
                    'Please use .txt, .xlsx, or .xls'
                )
        else:
            # Load default categories
            self.load_default_categories()

    def load_from_txt(self, file_path):
        """
        Load categories from a txt file.
        Format: key|name|description (one per line)
        Example: transport|Material Transport|Cost of transporting materials to site
        """
        self.stdout.write(f'Loading expense categories from {file_path}...')
        
        created_count = 0
        updated_count = 0
        error_count = 0

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue

                    # Parse the line
                    parts = line.split('|')
                    if len(parts) < 2:
                        self.stdout.write(
                            self.style.WARNING(
                                f'Line {line_num}: Invalid format (need at least key|name). Skipping.'
                            )
                        )
                        error_count += 1
                        continue

                    key = parts[0].strip()
                    name = parts[1].strip()
                    description = parts[2].strip() if len(parts) > 2 else ''

                    # Create or update category
                    category, created = ExpenseCategory.objects.update_or_create(
                        key=key,
                        defaults={
                            'name': name,
                            'description': description
                        }
                    )

                    if created:
                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'Created: {category.name} ({category.key})')
                        )
                    else:
                        updated_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'Updated: {category.name} ({category.key})')
                        )

        except Exception as e:
            raise CommandError(f'Error reading file: {str(e)}')

        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Successfully loaded expense categories!'
                f'\n  Created: {created_count}'
                f'\n  Updated: {updated_count}'
                f'\n  Errors: {error_count}'
            )
        )

    def load_from_excel(self, file_path):
        """
        Load categories from Excel file.
        Expected columns: key, name, description (optional)
        """
        try:
            import openpyxl
        except ImportError:
            raise CommandError(
                'openpyxl is required to read Excel files. '
                'Install it with: pip install openpyxl'
            )

        self.stdout.write(f'Loading expense categories from {file_path}...')

        created_count = 0
        updated_count = 0
        error_count = 0

        try:
            # Load workbook
            workbook = openpyxl.load_workbook(file_path)
            sheet = workbook.active

            # Get headers from first row
            headers = []
            for cell in sheet[1]:
                if cell.value:
                    headers.append(str(cell.value).strip().lower())

            # Validate required columns
            if 'key' not in headers or 'name' not in headers:
                raise CommandError(
                    'Excel file must have "key" and "name" columns in the first row'
                )

            key_col = headers.index('key')
            name_col = headers.index('name')
            desc_col = headers.index('description') if 'description' in headers else None

            # Process rows (skip header)
            for row_num, row in enumerate(sheet.iter_rows(min_row=2), 2):
                # Get values
                key = row[key_col].value
                name = row[name_col].value

                # Skip empty rows
                if not key or not name:
                    continue

                key = str(key).strip()
                name = str(name).strip()
                description = ''
                
                if desc_col is not None and row[desc_col].value:
                    description = str(row[desc_col].value).strip()

                try:
                    # Create or update category
                    category, created = ExpenseCategory.objects.update_or_create(
                        key=key,
                        defaults={
                            'name': name,
                            'description': description
                        }
                    )

                    if created:
                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'Created: {category.name} ({category.key})')
                        )
                    else:
                        updated_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'Updated: {category.name} ({category.key})')
                        )

                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f'Row {row_num}: Error creating category - {str(e)}'
                        )
                    )

        except Exception as e:
            raise CommandError(f'Error reading Excel file: {str(e)}')

        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Successfully loaded expense categories!'
                f'\n  Created: {created_count}'
                f'\n  Updated: {updated_count}'
                f'\n  Errors: {error_count}'
            )
        )

    def load_default_categories(self):
        """Load default expense categories"""
        self.stdout.write('Loading default expense categories...')

        default_categories = [
            {
                'key': 'transport',
                'name': 'Material Transport',
                'description': 'Cost of transporting materials from supplier to construction site'
            },
            {
                'key': 'licenses',
                'name': 'Government Licenses & Permits',
                'description': 'Fees for construction permits, licenses, and regulatory approvals'
            },
            {
                'key': 'transaction_fees',
                'name': 'Transaction Charges',
                'description': 'Bank fees, M-Pesa charges, and payment processing fees'
            },
            {
                'key': 'utilities',
                'name': 'Utilities',
                'description': 'Electricity, water, and other utility costs during construction'
            },
            {
                'key': 'equipment_rental',
                'name': 'Equipment Rental',
                'description': 'Rental fees for machinery, tools, and equipment'
            },
            {
                'key': 'professional_services',
                'name': 'Professional Services',
                'description': 'Fees for architects, engineers, surveyors, and consultants'
            },
            {
                'key': 'insurance',
                'name': 'Insurance',
                'description': 'Construction insurance, liability coverage, and worker compensation'
            },
            {
                'key': 'waste_disposal',
                'name': 'Waste Disposal',
                'description': 'Cost of removing construction debris and waste management'
            },
            {
                'key': 'security',
                'name': 'Security',
                'description': 'Security guards, fencing, and site protection'
            },
            {
                'key': 'office_supplies',
                'name': 'Office & Admin Supplies',
                'description': 'Stationery, printing, administrative materials'
            },
            {
                'key': 'inspection_fees',
                'name': 'Inspection Fees',
                'description': 'Fees for mandatory inspections and quality assurance tests'
            },
            {
                'key': 'contingency',
                'name': 'Contingency',
                'description': 'Unexpected expenses and miscellaneous costs'
            },
            {
                'key': 'food_accommodation',
                'name': 'Food & Accommodation',
                'description': 'Meals and accommodation for workers when applicable'
            },
            {
                'key': 'communication',
                'name': 'Communication',
                'description': 'Phone bills, internet, and communication expenses'
            },
            {
                'key': 'other',
                'name': 'Other Expenses',
                'description': 'Miscellaneous expenses not covered by other categories'
            },
        ]

        created_count = 0
        updated_count = 0

        for cat_data in default_categories:
            category, created = ExpenseCategory.objects.update_or_create(
                key=cat_data['key'],
                defaults={
                    'name': cat_data['name'],
                    'description': cat_data['description']
                }
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created: {category.name}')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Updated: {category.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Successfully loaded default expense categories!'
                f'\n  Created: {created_count}'
                f'\n  Updated: {updated_count}'
            )
        )


