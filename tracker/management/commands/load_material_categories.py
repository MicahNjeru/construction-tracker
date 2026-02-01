"""
Management command to load material categories into the database.

Usage:
    python manage.py load_material_categories material_categories.txt
    python manage.py load_material_categories material_categories.xls
    python manage.py load_material_categories material_categories.xlsx
"""

from django.core.management.base import BaseCommand
from tracker.models import MaterialCategory
import os


class Command(BaseCommand):
    help = 'Load material categories from a text or Excel file'

    def add_arguments(self, parser):
        parser.add_argument(
            'file_path',
            type=str,
            help='Path to the material categories file'
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

    # ---------------------------------------------------------------------

    def parse_line(self, line):
        """
        Parse a line using either pipe [|] or comma [,] as the separator.
        Returns a list of stripped values, or None if no valid separator is found.
        """
        if '|' in line:
            return [p.strip() for p in line.split('|', 1)]
        elif ',' in line:
            return [p.strip() for p in line.split(',', 1)]
        return None

    # ---------------------------------------------------------------------

    def load_from_text(self, file_path):
        """
        Expected format per line:
        key | name
        key , name
        """

        created = 0
        skipped = 0

        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                if not line or line.startswith('#'):
                    continue

                parts = self.parse_line(line)

                if not parts or len(parts) < 2:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Line {line_num}: Invalid format, skipping'
                        )
                    )
                    skipped += 1
                    continue

                key = parts[0]
                name = parts[1]

                if MaterialCategory.objects.filter(key=key).exists():
                    self.stdout.write(
                        self.style.WARNING(
                            f'Line {line_num}: Category "{key}" already exists'
                        )
                    )
                    skipped += 1
                    continue

                MaterialCategory.objects.create(key=key, name=name)
                self.stdout.write(
                    self.style.SUCCESS(f'Created category: {name}')
                )
                created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSummary: Created {created}, Skipped {skipped}'
            )
        )

    # ---------------------------------------------------------------------

    def load_from_excel(self, file_path):
        """
        Expected columns:
        key | name
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

        created = 0
        skipped = 0

        workbook = openpyxl.load_workbook(file_path)
        sheet = workbook.active

        for row_num, row in enumerate(
            sheet.iter_rows(min_row=2, values_only=True), 2
        ):
            if not row or not row[0] or not row[1]:
                continue

            key = str(row[0]).strip()
            name = str(row[1]).strip()

            if MaterialCategory.objects.filter(key=key).exists():
                self.stdout.write(
                    self.style.WARNING(
                        f'Row {row_num}: Category "{key}" already exists'
                    )
                )
                skipped += 1
                continue

            MaterialCategory.objects.create(key=key, name=name)
            self.stdout.write(
                self.style.SUCCESS(f'Created category: {name}')
            )
            created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSummary: Created {created}, Skipped {skipped}'
            )
        )