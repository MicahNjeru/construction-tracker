"""
Management command to load materials into the material catalog.

Usage:
    python manage.py load_materials materials.txt
    python manage.py load_materials materials.xls
    python manage.py load_materials materials.xlsx
"""

from django.core.management.base import BaseCommand
from tracker.models import MaterialCatalog, MaterialCategory, MaterialUnit
import os


class Command(BaseCommand):
    help = 'Load materials into the material catalog from a text or Excel file'

    def add_arguments(self, parser):
        parser.add_argument(
            'file_path',
            type=str,
            help='Path to the materials file'
        )

    def handle(self, *args, **options):
        file_path = options['file_path']

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'File not found: {file_path}'))
            return

        extension = os.path.splitext(file_path)[1].lower()

        if extension == '.txt':
            self.load_from_text(file_path)
        elif extension in ['.xlsx', '.xls']:
            self.load_from_excel(file_path)
        else:
            self.stdout.write(
                self.style.ERROR('Unsupported file format. Use .txt, .xls or .xlsx')
            )

    # ------------------------------------------------------------------

    def load_from_text(self, file_path):
        """
        Expected format per line:
        category_key | description | unit_name | cost
        """

        created_count = 0
        skipped_count = 0

        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                if not line or line.startswith('#'):
                    continue

                parts = [p.strip() for p in line.split('|')]

                if len(parts) < 3:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Line {line_num}: Invalid format, skipping'
                        )
                    )
                    skipped_count += 1
                    continue

                category_key = parts[0]
                description = parts[1]
                unit_name = parts[2]
                cost = parts[3] if len(parts) > 3 else 0

                # Resolve category
                try:
                    category = MaterialCategory.objects.get(key=category_key)
                except MaterialCategory.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(
                            f'Line {line_num}: Unknown category "{category_key}"'
                        )
                    )
                    skipped_count += 1
                    continue

                # Resolve unit (optional but validated)
                unit = MaterialUnit.objects.filter(name=unit_name).first()
                if not unit:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Line {line_num}: Unit "{unit_name}" not found, setting unit=NULL'
                        )
                    )

                # Deduplication check
                if MaterialCatalog.objects.filter(
                    category=category,
                    description=description
                ).exists():
                    self.stdout.write(
                        self.style.WARNING(
                            f'Line {line_num}: "{category.name} - {description}" already exists'
                        )
                    )
                    skipped_count += 1
                    continue

                MaterialCatalog.objects.create(
                    category=category,
                    description=description,
                    default_unit=unit,
                    default_cost=cost
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created: {category.name} - {description}'
                    )
                )
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSummary: Created {created_count}, Skipped {skipped_count}'
            )
        )

    # ------------------------------------------------------------------

    def load_from_excel(self, file_path):
        """
        Expected columns:
        category_key | description | unit_name | cost
        """

        try:
            import openpyxl
        except ImportError:
            self.stdout.write(
                self.style.ERROR(
                    'openpyxl is required. Install with: pip install openpyxl'
                )
            )
            return

        created_count = 0
        skipped_count = 0

        workbook = openpyxl.load_workbook(file_path)
        sheet = workbook.active

        for row_num, row in enumerate(
            sheet.iter_rows(min_row=2, values_only=True), 2
        ):
            if not row or not row[0] or not row[1]:
                continue

            category_key = str(row[0]).strip()
            description = str(row[1]).strip()
            unit_name = str(row[2]).strip() if len(row) > 2 and row[2] else ''
            cost = row[3] if len(row) > 3 and row[3] else 0

            # Resolve category
            try:
                category = MaterialCategory.objects.get(key=category_key)
            except MaterialCategory.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(
                        f'Row {row_num}: Unknown category "{category_key}"'
                    )
                )
                skipped_count += 1
                continue

            # Resolve unit
            unit = MaterialUnit.objects.filter(name=unit_name).first()
            if not unit:
                self.stdout.write(
                    self.style.WARNING(
                        f'Row {row_num}: Unit "{unit_name}" not found, setting unit=NULL'
                    )
                )

            if MaterialCatalog.objects.filter(
                category=category,
                description=description
            ).exists():
                self.stdout.write(
                    self.style.WARNING(
                        f'Row {row_num}: "{category.name} - {description}" already exists'
                    )
                )
                skipped_count += 1
                continue

            MaterialCatalog.objects.create(
                category=category,
                description=description,
                default_unit=unit,
                default_cost=cost
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f'Created: {category.name} - {description}'
                )
            )
            created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSummary: Created {created_count}, Skipped {skipped_count}'
            )
        )
