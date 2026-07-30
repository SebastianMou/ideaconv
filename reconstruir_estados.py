# ============================================================================
#  reconstruir_estados.py
#  Rebuilds the deleted EstadoDeCuenta history from investment data.
#
#  HOW TO RUN (Railway → your DJANGO/web service → Console tab, NOT Postgres):
#
#      python manage.py shell < reconstruir_estados.py
#
#  or paste it after running:  python manage.py shell
#
#  SAFETY: DRY_RUN is True by default. It prints what it WOULD create and
#  writes NOTHING. Review the output, then set DRY_RUN = False and run again
#  to actually create the records.
# ============================================================================

from decimal import Decimal
from datetime import date, timedelta
import calendar

from django.apps import apps
from django.db import transaction

# ── locate models without needing to know the app label ──
def M(name):
    return next(m for m in apps.get_models() if m.__name__ == name)

Inversionista  = M('Inversionista')
Inversion      = M('Inversion')
EstadoDeCuenta = M('EstadoDeCuenta')
Pago           = M('Pago')

# ── CONFIG ──────────────────────────────────────────────────────────────────
DRY_RUN     = True          # ← set to False to actually write to the database
START_YEAR  = 2026
START_MONTH = 5             # May
END_YEAR    = date.today().year
END_MONTH   = date.today().month   # up to and including the current month
ISR_RATE    = Decimal('0.20')
IVA_RATE    = Decimal('0.16')
# ─────────────────────────────────────────────────────────────────────────────


def meses_en_rango(y1, m1, y2, m2):
    """Yield (year, month) from start to end inclusive."""
    y, m = y1, m1
    while (y, m) <= (y2, m2):
        yield y, m
        m += 1
        if m > 12:
            m = 1
            y += 1


def interes_periodo(inv, p_inicio, p_fin):
    """
    Gross interest for `inv` over [p_inicio, p_fin], corrected for back-dated
    periods: the opening balance is reconstructed by reversing EVERY movement
    dated on/after p_inicio (not just those inside the period), then walking
    forward through the in-period movements as pro-rated tranches.
    """
    tasa = inv.tasa_anual / Decimal('100')
    base = Decimal(str(inv.base_calculo))

    # interest starts the day AFTER the investment's start date
    if inv.fecha_inicio:
        efectivo_inicio = max(p_inicio, inv.fecha_inicio + timedelta(days=1))
    else:
        efectivo_inicio = p_inicio

    # opening balance at the start of THIS period = today's capital with every
    # movement from p_inicio onward reversed out
    capital_apertura = inv.capital
    for mov in inv.movimientos.filter(fecha__gte=p_inicio):
        if mov.tipo == 'abono':
            capital_apertura -= mov.monto
        else:
            capital_apertura += mov.monto

    # in-period movements, chronological
    movs = list(inv.movimientos.filter(fecha__gte=p_inicio, fecha__lte=p_fin).order_by('fecha'))

    tranches       = []
    capital_actual = capital_apertura
    tranche_start  = efectivo_inicio

    for mov in movs:
        if mov.fecha > tranche_start:
            dias_t = Decimal(str((mov.fecha - tranche_start).days))
            if dias_t > 0 and capital_actual > 0:
                tranches.append((capital_actual, dias_t))
        if mov.tipo == 'abono':
            capital_actual += mov.monto
        else:
            capital_actual -= mov.monto
        tranche_start = max(mov.fecha, efectivo_inicio)

    dias_finales = Decimal(str((p_fin - tranche_start).days + 1))
    if dias_finales > 0 and capital_actual > 0:
        tranches.append((capital_actual, dias_finales))

    bruto = Decimal('0')
    for cap_t, dias_t in tranches:
        bruto += cap_t * (tasa / base) * dias_t
    return bruto.quantize(Decimal('0.01'))


def periodo_para(inv_ista, year, month):
    """Return (p_inicio, p_fin, dias_periodo) for an investor & month."""
    p_inicio = date(year, month, 1)
    if inv_ista.dias_cierre_fijo:                      # fixed-days investors (e.g. always 30)
        dias = inv_ista.dias_cierre_fijo
        p_fin = p_inicio + timedelta(days=dias - 1)
    else:                                              # normal: full calendar month
        last_day = calendar.monthrange(year, month)[1]
        p_fin = date(year, month, last_day)
        dias = (p_fin - p_inicio).days + 1
    return p_inicio, p_fin, dias


# ── MAIN ─────────────────────────────────────────────────────────────────────
inversionistas = Inversionista.objects.filter(eliminado=False).prefetch_related('inversiones')

plan = []          # rows we intend to create
saltados_exist = 0 # already-present periods

for inv_ista in inversionistas:
    for (year, month) in meses_en_rango(START_YEAR, START_MONTH, END_YEAR, END_MONTH):
        p_inicio, p_fin, dias_periodo = periodo_para(inv_ista, year, month)

        # skip if an estado already exists for this investor+period
        if EstadoDeCuenta.objects.filter(inversionista=inv_ista, periodo_inicio=p_inicio).exists():
            saltados_exist += 1
            continue

        # only investments that existed by the end of this period
        inversiones = inv_ista.inversiones.filter(estado='activo', fecha_inicio__lte=p_fin)
        if not inversiones.exists():
            continue

        total_bruto = total_isr = total_iva = total_externo = Decimal('0')
        for inv in inversiones:
            pct_factura = inv.porcentaje_factura / Decimal('100')
            pct_externo = Decimal('1') - pct_factura
            bruto   = interes_periodo(inv, p_inicio, p_fin)
            fact    = bruto * pct_factura
            total_bruto   += bruto
            total_isr     += fact * ISR_RATE
            total_iva     += fact * IVA_RATE
            total_externo += bruto * pct_externo

        if total_bruto == 0:
            continue

        subtotal_fact = (total_bruto - total_externo) - total_isr
        interes_neto  = subtotal_fact + total_iva
        total_pagar   = interes_neto + total_externo

        plan.append(dict(
            inv_ista=inv_ista, p_inicio=p_inicio, p_fin=p_fin, dias=dias_periodo,
            bruto=total_bruto.quantize(Decimal('0.01')),
            isr=total_isr.quantize(Decimal('0.01')),
            iva=total_iva.quantize(Decimal('0.01')),
            neto=interes_neto.quantize(Decimal('0.01')),
            externo=total_externo.quantize(Decimal('0.01')),
            total=total_pagar.quantize(Decimal('0.01')),
        ))

# ── report ──
print("=" * 78)
print(f"Rango: {START_YEAR}-{START_MONTH:02d}  →  {END_YEAR}-{END_MONTH:02d}")
print(f"Estados a crear: {len(plan)}   |   ya existentes (saltados): {saltados_exist}")
print("=" * 78)
for r in plan:
    print(f"{r['p_inicio']} → {r['p_fin']} ({r['dias']}d)  "
          f"{r['inv_ista'].nombre_completo[:34]:34}  total ${r['total']}")
print("=" * 78)

if DRY_RUN:
    print("DRY_RUN = True  →  nada se escribió. Revisa la lista de arriba.")
    print("Cuando esté correcta, cambia DRY_RUN = False y vuelve a correr.")
else:
    with transaction.atomic():
        creados = 0
        for r in plan:
            estado = EstadoDeCuenta.objects.create(
                inversionista=r['inv_ista'],
                inversion=None,
                periodo_inicio=r['p_inicio'],
                periodo_fin=r['p_fin'],
                dias_periodo=r['dias'],
                interes_bruto=r['bruto'],
                isr=r['isr'],
                iva=r['iva'],
                interes_neto=r['neto'],
                pago_externo=r['externo'],
                total_pagar=r['total'],
                estado=('generado'
            )
            Pago.objects.get_or_create(
                estado_de_cuenta=estado,
                defaults={'metodo': 'transferencia', 'estado': 'pendiente'},
            )
            creados += 1
    print(f"✅ LISTO. {creados} estados de cuenta reconstruidos.")