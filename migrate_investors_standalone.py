"""
Standalone Investor Migration Script
=====================================

This script can be run in Django shell:
    python manage.py shell < migrate_investors.py

Or copy-paste it into the shell.

It will:
1. Load inversionistas_migration.json
2. Update existing investors by name match
3. Create new investors if not found
4. Handle promotor creation automatically
"""

import json
import re
from datetime import datetime
from decimal import Decimal

# Import your models - adjust the app name
from inversiones.models import Inversionista, Promotor

# Configuration
JSON_FILE_PATH = 'inversionistas_migration.json'
DRY_RUN = False  # Set to False to actually save changes

def normalize_name(name):
    """Normalize name for matching"""
    if not name:
        return ''
    return re.sub(r'\s+', ' ', str(name).strip().upper())

def get_or_create_promotor(nombre):
    """Get or create a Promotor by name"""
    if not nombre:
        return None
    
    # First, try to find existing promotor by name (case-insensitive)
    try:
        promotor = Promotor.objects.get(nombre__iexact=nombre)
        return promotor
    except Promotor.DoesNotExist:
        # Create new promotor
        try:
            promotor = Promotor.objects.create(
                nombre=nombre,
                activo=True
            )
            print(f"  ➕ Created promotor: {nombre}")
            return promotor
        except Exception as e:
            # If creation fails, try to find by exact match one more time
            try:
                promotor = Promotor.objects.get(nombre=nombre)
                return promotor
            except:
                print(f"  ⚠️  Warning: Could not create/find promotor '{nombre}': {e}")
                return None

# Load migration data
print(f"📂 Loading data from {JSON_FILE_PATH}...")
with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
    migration_data = json.load(f)

print(f"✅ Loaded {len(migration_data)} records")

if DRY_RUN:
    print("🔍 DRY RUN MODE - No changes will be saved\n")
else:
    print("⚠️  LIVE MODE - Changes will be saved!\n")

# Statistics
stats = {
    'updated': 0,
    'created': 0,
    'skipped': 0,
    'errors': 0,
    'promotores_created': 0
}

errors = []

# Process each record
for idx, record in enumerate(migration_data, 1):
    excel_id = record.get('excel_id', '?')
    nombre = record.get('nombre_completo', '')
    nombre_normalized = record.get('nombre_completo_normalized', '')
    
    if not nombre_normalized:
        print(f"⚠️  [{idx}] Excel ID {excel_id}: No name, skipping")
        stats['skipped'] += 1
        continue
    
    try:
        # Try to find existing investor by normalized name
        existing = None
        
        # Search by exact normalized name
        for inv in Inversionista.objects.filter(eliminado=False):
            if normalize_name(inv.nombre_completo) == nombre_normalized:
                existing = inv
                break
        
        if existing:
            # UPDATE existing record
            action = "UPDATE"
            investor = existing
            print(f"🔄 [{idx}] Updating: {nombre} (DB ID: {investor.id})")
        else:
            # CREATE new record
            action = "CREATE"
            investor = Inversionista()
            stats['created'] += 1
            print(f"➕ [{idx}] Creating: {nombre}")
        
        # Update all fields from Excel
        investor.nombre_completo = nombre
        investor.tipo_contribuyente = record.get('tipo_contribuyente', 'fisica')
        investor.curp = record.get('curp') or None
        investor.rfc = record.get('rfc') or None
        investor.correo = record.get('correo', '')
        investor.telefono = record.get('telefono', '')
        investor.nacionalidad = record.get('nacionalidad', 'Mexicana')
        
        # Fecha de nacimiento
        fecha_nac = record.get('fecha_nacimiento')
        if fecha_nac:
            try:
                investor.fecha_nacimiento = datetime.strptime(fecha_nac, '%Y-%m-%d').date()
            except:
                pass
        
        # Domicilio
        investor.calle = record.get('calle', '')
        investor.ciudad = record.get('ciudad', '')
        investor.estado = record.get('estado', '')
        investor.codigo_postal = record.get('codigo_postal', '')
        
        # Datos fiscales
        investor.pais_fiscal = record.get('pais_fiscal', 'México')
        investor.estado_fiscal = record.get('estado_fiscal', '')
        investor.cp_fiscal = record.get('cp_fiscal', '')
        investor.nombre_fiscal = record.get('nombre_fiscal', '')
        
        # Datos bancarios
        investor.banco = record.get('banco', '')
        investor.clabe = record.get('clabe', '')
        
        # Promotor
        promotor_nombre = record.get('promotor_nombre')
        if promotor_nombre:
            promotor = get_or_create_promotor(promotor_nombre)
            if promotor:
                investor.promotor = promotor
        
        # Save
        if not DRY_RUN:
            investor.save()
            print(f"    💾 Saved to database")
        
        if action == "UPDATE":
            stats['updated'] += 1
        
        # Show what changed
        changes = []
        if record.get('rfc'):
            changes.append(f"RFC: {record.get('rfc')}")
        if record.get('correo'):
            changes.append(f"Email: {record.get('correo')}")
        if record.get('telefono'):
            changes.append(f"Tel: {record.get('telefono')[:15]}...")
        if changes:
            print(f"    📝 {', '.join(changes[:3])}")
    
    except Exception as e:
        stats['errors'] += 1
        error_msg = f"[{idx}] Excel ID {excel_id} ({nombre}): {str(e)}"
        errors.append(error_msg)
        print(f"❌ {error_msg}")

# Final report
print("\n" + "="*60)
print("📊 MIGRATION REPORT")
print("="*60)
print(f"✅ Updated: {stats['updated']}")
print(f"➕ Created: {stats['created']}")
print(f"⏭️  Skipped: {stats['skipped']}")
print(f"❌ Errors: {stats['errors']}")
print(f"📝 Total processed: {len(migration_data)}")

if errors:
    print("\n" + "="*60)
    print("❌ ERRORS:")
    for error in errors:
        print(f"  • {error}")

if DRY_RUN:
    print("\n⚠️  This was a DRY RUN - no changes were saved")
    print("Set DRY_RUN = False to apply changes")
else:
    print("\n✅ Migration completed successfully!")