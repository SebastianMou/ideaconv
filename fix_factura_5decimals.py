"""
fix_factura_5decimals.py
Truncates all porcentaje_factura values to 5 decimal places.

Run BEFORE the migration:
    python manage.py shell < fix_factura_5decimals.py
"""
from decimal import Decimal, ROUND_DOWN
from inversiones.models import Inversion

updated = 0
for inv in Inversion.objects.all():
    truncated = inv.porcentaje_factura.quantize(Decimal('0.00000'), rounding=ROUND_DOWN)
    if truncated != inv.porcentaje_factura:
        print(f"  id={inv.id:<4d}  {inv.inversionista.nombre_completo[:35]:<35}  {inv.porcentaje_factura} → {truncated}")
        inv.porcentaje_factura = truncated
        inv.save(update_fields=['porcentaje_factura'])
        updated += 1

print(f"\n✅ {updated} records truncated to 5 decimal places.")