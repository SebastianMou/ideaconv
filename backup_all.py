"""
Complete Database Backup - All in One
======================================

Run this script to backup your entire database to JSON.

Usage:
    python manage.py shell < backup_all.py

Output:
    Creates: backup_complete_YYYY-MM-DD_HHMMSS.json
"""

from django.core import serializers
from datetime import datetime
import json

from inversiones.models import (
    Inversionista, Inversion, Promotor, EstadoDeCuenta, 
    Pago, Prospecto, Movimiento, HoneypotAttempt,
    BugReport, NotificacionDismissed
)

# Create filename with timestamp
timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
filename = f'backup_complete_{timestamp}.json'

print("="*60)
print("📦 COMPLETE DATABASE BACKUP")
print("="*60)

# Collect all data
all_objects = []
stats = {}

models = [
    (Promotor, 'Promotores'),
    (Inversionista, 'Inversionistas'),
    (Inversion, 'Inversiones'),
    (Movimiento, 'Movimientos'),
    (EstadoDeCuenta, 'Estados de Cuenta'),
    (Pago, 'Pagos'),
    (Prospecto, 'Prospectos'),
    (HoneypotAttempt, 'Honeypot Attempts'),
    (BugReport, 'Bug Reports'),
    (NotificacionDismissed, 'Notificaciones Dismissed'),
]

print("\n📊 Collecting data...")
total = 0
for model, name in models:
    count = model.objects.count()
    stats[name] = count
    print(f"  • {name}: {count} records")
    all_objects.extend(model.objects.all())
    total += count

# Serialize to JSON
print(f"\n💾 Serializing {total} records...")
data = serializers.serialize('json', all_objects, indent=2)

# Save to file
print(f"💾 Writing to {filename}...")
with open(filename, 'w', encoding='utf-8') as f:
    f.write(data)

# Calculate file size
file_size_kb = len(data) / 1024
file_size_mb = file_size_kb / 1024

print("\n" + "="*60)
print("✅ BACKUP COMPLETED!")
print("="*60)
print(f"📄 File: {filename}")
if file_size_mb >= 1:
    print(f"📊 Size: {file_size_mb:.2f} MB")
else:
    print(f"📊 Size: {file_size_kb:.2f} KB")
print(f"📝 Total records: {total}")

print("\n📋 Breakdown:")
for name, count in stats.items():
    print(f"  • {name}: {count}")

print("\n💡 To restore this backup:")
print(f"   python manage.py loaddata {filename}")
print("\n🎉 Your data is safe!")