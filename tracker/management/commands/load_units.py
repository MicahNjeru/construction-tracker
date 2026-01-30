"""
Management command to load material units from a text or Excel file.

Usage:
    python manage.py load_units units.txt
    python manage.py load_units units.xlx
    python manage.py load_units units.xlsx
"""
from django.core.management.base import BaseCommand
from tracker.models import MaterialUnit
import os


class Command(BaseCommand):
    help = 'Load material units from a text or Excel file'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to the file containing units')

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
            self.stdout.write(self.style.ERROR('Unsupported file format. Use .txt or .xlsx'))
    
    def load_from_text(self, file_path):
        """
        Load units from text file.
        Expected format (one per line):
        unit_name,abbreviation
        OR
        unit_name|abbreviation
        """
        created_count = 0
        skipped_count = 0
        
        with open(file_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Support both comma and pipe as separator
                if ',' in line:
                    parts = line.split(',')
                elif '|' in line:
                    parts = line.split('|')
                else:
                    parts = [line, line[:3]]  # Use first 3 chars as abbreviation
                
                if len(parts) >= 2:
                    name = parts[0].strip()
                    abbreviation = parts[1].strip()
                else:
                    name = parts[0].strip()
                    abbreviation = name[:3]
                
                if MaterialUnit.objects.filter(name=name).exists():
                    self.stdout.write(self.style.WARNING(f'Line {line_num}: Unit "{name}" already exists, skipping'))
                    skipped_count += 1
                else:
                    MaterialUnit.objects.create(name=name, abbreviation=abbreviation)
                    self.stdout.write(self.style.SUCCESS(f'Created unit: {name} ({abbreviation})'))
                    created_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'\nSummary: Created {created_count} units, Skipped {skipped_count} units'))
    
    def load_from_excel(self, file_path):
        """
        Load units from Excel file.
        Expected columns: name, abbreviation
        """
        try:
            import openpyxl
        except ImportError:
            self.stdout.write(self.style.ERROR('openpyxl is required for Excel support. Install it with: pip install openpyxl'))
            return
        
        created_count = 0
        skipped_count = 0
        
        workbook = openpyxl.load_workbook(file_path)
        sheet = workbook.active
        
        # Skip header row
        for row_num, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), 2):
            if not row[0]:
                continue
            
            name = str(row[0]).strip()
            abbreviation = str(row[1]).strip() if len(row) > 1 and row[1] else name[:3]
            
            if MaterialUnit.objects.filter(name=name).exists():
                self.stdout.write(self.style.WARNING(f'Row {row_num}: Unit "{name}" already exists, skipping'))
                skipped_count += 1
            else:
                MaterialUnit.objects.create(name=name, abbreviation=abbreviation)
                self.stdout.write(self.style.SUCCESS(f'Created unit: {name} ({abbreviation})'))
                created_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'\nSummary: Created {created_count} units, Skipped {skipped_count} units'))