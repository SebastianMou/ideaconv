# ============================================================================
#  diagnostico_saldos.py   —   SOLO LECTURA (no escribe nada en la base)
#
#  Correr desde la raíz del proyecto (con el venv activado y en LOCAL):
#      python manage.py shell < diagnostico_saldos.py
#
#  Muestra, para los 4 inversionistas reportados, cada inversión con su
#  estado / capital / fechas, y compara el saldo ACTIVO-only contra el
#  objetivo que dio el jefe.
# ============================================================================

import unicodedata
from decimal import Decimal
from inversiones.models import Inversionista


def norm(s):
    """Uppercase, quita acentos y colapsa espacios — para emparejar nombres."""
    if not s:
        return ''
    s = unicodedata.normalize('NFKD', str(s))
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return ' '.join(s.upper().split())


# (fragmento del nombre, saldo correcto según el jefe)
TARGETS = [
    ('ALVARO DIAZ CAMPOS',         Decimal('10000000')),
    ('SALVADOR DIAZ CAMPOS',       Decimal('6500000')),
    ('ELIAS ALBERTO GARCIA CANTU', Decimal('38000000')),
    ('NEREO RIVERA GONZALEZ',      Decimal('2350000')),
]

todos = list(Inversionista.objects.all())

for frag, objetivo in TARGETS:
    print('=' * 92)
    matches = [i for i in todos if frag in norm(i.nombre_completo)]
    if not matches:
        print(f'NO ENCONTRADO: {frag}')
        continue

    for inv_ista in matches:
        print(f'{inv_ista.nombre_completo}   (id={inv_ista.id}, eliminado={inv_ista.eliminado})')
        print('-' * 92)
        print(f'{"Folio":<9}{"Estado":<11}{"Capital":>16}  '
              f'{"Inicio":<12}{"Vencimiento":<13}{"Renov#":>7}{"RenovDe":>9}')

        suma_todas = suma_activo = suma_vencido = Decimal('0')
        for inv in inv_ista.inversiones.all().order_by('id'):
            cap = inv.capital or Decimal('0')
            suma_todas += cap
            if inv.estado == 'activo':
                suma_activo += cap
            elif inv.estado == 'vencido':
                suma_vencido += cap
            print(f'INV-{inv.id:<5}{inv.estado:<11}{cap:>16,.2f}  '
                  f'{str(inv.fecha_inicio or "—"):<12}'
                  f'{str(inv.fecha_vencimiento or "—"):<13}'
                  f'{inv.numero_renovacion:>7}{str(inv.renovacion_de_id or "—"):>9}')

        ok = 'OK ✓' if suma_activo == objetivo else 'DIFERENCIA ✗'
        print('-' * 92)
        print(f'   Suma TODAS:     {suma_todas:>16,.2f}')
        print(f'   Suma VENCIDO:   {suma_vencido:>16,.2f}   (NO debe entrar al saldo)')
        print(f'   Suma ACTIVO:    {suma_activo:>16,.2f}   <- saldo correcto propuesto')
        print(f'   Objetivo jefe:  {objetivo:>16,.2f}')
        print(f'   Resultado:      {ok}')

print('=' * 92)
print('Script de SOLO LECTURA — no se modificó ningún dato.')