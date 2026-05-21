"""
Django Management Command for Syscap Data Import
=================================================
Place this file in: inversiones/management/commands/import_syscap.py

Usage:
    python manage.py import_syscap django_fixtures.json
    python manage.py import_syscap django_fixtures.json --dry-run
    python manage.py import_syscap django_fixtures.json --validate-only
"""

from attrs import fields
from django.core.management.base import BaseCommand
from django.db import transaction
from inversiones.models import (
    Promotor, Inversionista, Inversion, Movimiento,
    EstadoDeCuenta, Pago, Prospecto
)
import json
from decimal import Decimal
from datetime import datetime, date


class Command(BaseCommand):
    help = 'Import data from Syscap migration JSON file'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='Path to django_fixtures.json')
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Validate without importing',
        )
        parser.add_argument(
            '--validate-only',
            action='store_true',
            help='Only validate the JSON structure',
        )
        parser.add_argument(
            '--skip-duplicates',
            action='store_true',
            help='Skip records that might be duplicates',
        )

    def handle(self, *args, **options):
        json_file = options['json_file']
        dry_run = options['dry_run']
        validate_only = options['validate_only']
        skip_duplicates = options['skip_duplicates']

        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('SYSCAP DATA IMPORT'))
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))

        # Load JSON
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'❌ File not found: {json_file}'))
            return
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'❌ Invalid JSON: {e}'))
            return

        self.stdout.write(f'📂 Loaded {len(data)} records from {json_file}\n')

        # Group by model
        grouped = self._group_by_model(data)
        
        # Validate
        validation_errors = self._validate_data(grouped)
        
        if validation_errors:
            self.stdout.write(self.style.ERROR('\n❌ VALIDATION ERRORS:\n'))
            for error in validation_errors:
                self.stdout.write(self.style.ERROR(f'  • {error}'))
            return

        self.stdout.write(self.style.SUCCESS('✅ Validation passed\n'))

        if validate_only:
            self.stdout.write(self.style.SUCCESS('Validation complete (--validate-only mode)'))
            return

        # Show summary
        self._show_import_summary(grouped)

        if dry_run:
            self.stdout.write(self.style.WARNING('\n🔍 DRY RUN MODE - No data will be imported'))
            return

        # Confirm
        confirm = input('\n⚠️  This will import data into your database. Continue? (yes/no): ')
        if confirm.lower() != 'yes':
            self.stdout.write(self.style.WARNING('Import cancelled'))
            return

        # Import
        self._import_data(grouped, skip_duplicates)

    def _group_by_model(self, data):
        """Group records by model"""
        grouped = {
            'inversiones.promotor': [],
            'inversiones.inversionista': [],
            'inversiones.inversion': [],
            'inversiones.movimiento': [],
            'inversiones.estadodecuenta': [],
            'inversiones.pago': [],
            'inversiones.prospecto': []
        }
        
        for record in data:
            model = record.get('model')
            if model in grouped:
                grouped[model].append(record)
        
        return grouped

    def _validate_data(self, grouped):
        """Validate the data structure"""
        errors = []
        
        # Check required models
        if not grouped['inversiones.promotor']:
            errors.append('No promoters found')
        
        if not grouped['inversiones.inversionista']:
            errors.append('No investors found')
        
        # Validate promoter records
        for record in grouped['inversiones.promotor']:
            fields = record.get('fields', {})
            if not fields.get('nombre'):
                errors.append(f"Promoter {record.get('pk')} missing name")
        
        # Validate investor records
        for record in grouped['inversiones.inversionista']:
            fields = record.get('fields', {})
            if not fields.get('nombre_completo'):
                errors.append(f"Investor {record.get('pk')} missing name")
            
            # Check RFC format (allow empty/null, just warn on invalid)
            rfc = fields.get('rfc')
            # Skip validation - Syscap data has incomplete RFCs
        
        # Validate investment records
        for record in grouped['inversiones.inversion']:
            fields = record.get('fields', {})
            if not fields.get('inversionista'):
                errors.append(f"Investment {record.get('pk')} missing investor reference")
            
            try:
                capital = Decimal(str(fields.get('capital', 0)))
                # Allow zero/negative for historical records
                # if capital <= 0:
                #     errors.append(f"Investment {record.get('pk')} has invalid capital: {capital}")
            except:
                errors.append(f"Investment {record.get('pk')} has invalid capital format")

        return errors

    def _show_import_summary(self, grouped):
        """Display import summary"""
        self.stdout.write(self.style.SUCCESS('📊 IMPORT SUMMARY:\n'))
        
        summary = [
            ('Promotores', len(grouped['inversiones.promotor'])),
            ('Inversionistas', len(grouped['inversiones.inversionista'])),
            ('Inversiones', len(grouped['inversiones.inversion'])),
            ('Movimientos', len(grouped['inversiones.movimiento'])),
            ('Estados de Cuenta', len(grouped['inversiones.estadodecuenta'])),
            ('Pagos', len(grouped['inversiones.pago'])),
            ('Prospectos', len(grouped['inversiones.prospecto']))
        ]
        
        for label, count in summary:
            if count > 0:
                self.stdout.write(f'  • {label}: {count}')

    @transaction.atomic
    def _import_data(self, grouped, skip_duplicates):
        """Import the data in correct order"""
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('IMPORTING DATA'))
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))

        stats = {
            'created': 0,
            'skipped': 0,
            'errors': 0
        }

        # Order matters due to foreign keys
        import_order = [
            ('inversiones.promotor', Promotor, 'Promotores'),
            ('inversiones.inversionista', Inversionista, 'Inversionistas'),
            ('inversiones.prospecto', Prospecto, 'Prospectos'),
            ('inversiones.inversion', Inversion, 'Inversiones'),
            ('inversiones.movimiento', Movimiento, 'Movimientos'),
            ('inversiones.estadodecuenta', EstadoDeCuenta, 'Estados de Cuenta'),
            ('inversiones.pago', Pago, 'Pagos')
        ]

        for model_name, model_class, label in import_order:
            records = grouped[model_name]
            if not records:
                continue

            self.stdout.write(f'\n📥 Importing {label}...')
            
            for record in records:
                try:
                    pk = record.get('pk')
                    fields = record.get('fields', {})
                    
                    # Check for duplicates
                    if skip_duplicates:
                        if model_class.objects.filter(pk=pk).exists():
                            stats['skipped'] += 1
                            continue
                    
                    # Handle date fields
                    fields = self._convert_dates(fields)
                    
                    # Convert foreign key IDs to instances
                    has_missing_required_fk = False
                    for field_name, field_value in fields.items():
                        try:
                            field_obj = model_class._meta.get_field(field_name)
                            if field_obj.related_model and field_value:
                                # It's a foreign key - convert ID to instance
                                try:
                                    fields[field_name] = field_obj.related_model.objects.get(pk=field_value)
                                except field_obj.related_model.DoesNotExist:
                                    # Check if this FK is required (not nullable)
                                    if not field_obj.null:
                                        has_missing_required_fk = True
                                        self.stdout.write(
                                            self.style.WARNING(f'  ⚠️  Skipping {label} #{pk}: missing required {field_name}')
                                        )
                                        break
                                    fields[field_name] = None
                        except:
                            pass

                    # Skip if missing required FK
                    if has_missing_required_fk:
                        stats['skipped'] += 1
                        continue

                    # Create or update
                    obj, created = model_class.objects.update_or_create(
                        pk=pk,
                        defaults=fields
                    )
                    
                    stats['created'] += 1
                    
                except Exception as e:
                    stats['errors'] += 1
                    self.stdout.write(
                        self.style.ERROR(f'  ❌ Error importing {label} #{pk}: {e}')
                    )

            self.stdout.write(
                self.style.SUCCESS(f'  ✓ Completed: {label}')
            )

        # Show final stats
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('IMPORT COMPLETE'))
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))
        self.stdout.write(f"✅ Created/Updated: {stats['created']}")
        self.stdout.write(f"⏭️  Skipped: {stats['skipped']}")
        if stats['errors'] > 0:
            self.stdout.write(self.style.ERROR(f"❌ Errors: {stats['errors']}"))
        self.stdout.write('\n')

    def _convert_dates(self, fields):
        """Convert date strings to date objects"""
        date_fields = [
            'fecha_registro', 'fecha_nacimiento', 'fecha_ingreso',
            'fecha_inicio', 'fecha_vencimiento', 'fecha_eliminado',
            'fecha_pago', 'periodo_inicio', 'periodo_fin', 'fecha'
        ]
        
        for field in date_fields:
            if field in fields and fields[field]:
                try:
                    if isinstance(fields[field], str):
                        # Handle both date and datetime strings
                        if 'T' in fields[field]:
                            fields[field] = datetime.fromisoformat(fields[field].replace('Z', '+00:00'))
                        else:
                            fields[field] = datetime.strptime(fields[field], '%Y-%m-%d').date()
                except:
                    fields[field] = None
        
        return fields
