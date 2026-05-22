"""
Quick diagnostic - check existing promotores
Run: python manage.py shell < check_promotores.py
"""

from inversiones.models import Promotor

print("📊 Current Promotores in Database:")
print("="*60)

promotores = Promotor.objects.all().order_by('id')

if promotores.count() == 0:
    print("No promotores found")
else:
    for p in promotores:
        print(f"ID: {p.id:3d} | {p.nombre} | Activo: {p.activo} | Inversionistas: {p.inversionistas.count()}")

print(f"\nTotal: {promotores.count()} promotores")