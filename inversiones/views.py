from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import (
    Promotor, Inversionista, Inversion,
    EstadoDeCuenta, Pago, Prospecto
)
from .serializers import (
    PromotorSerializer, InversionistaSerializer, InversionistaListSerializer,
    InversionSerializer, EstadoDeCuentaSerializer, PagoSerializer,
    ProspectoSerializer, CalculadoraInputSerializer
)


# ══════════════════════════════════════════════
#  AUTH VIEWS
# ══════════════════════════════════════════════

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect(request.GET.get('next', 'dashboard'))
        return render(request, 'inversiones/login.html', {
            'error': 'Usuario o contraseña incorrectos.',
            'username': username,
        })

    return render(request, 'inversiones/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


# ══════════════════════════════════════════════
#  TEMPLATE VIEWS  (render HTML pages)
# ══════════════════════════════════════════════

@login_required(login_url='login')
def dashboard_view(request):
    return render(request, 'inversiones/dashboard.html')

@login_required(login_url='login')
def inversionistas_view(request):
    return render(request, 'inversiones/inversionistas.html')

@login_required(login_url='login')
def calculadora_view(request):
    return render(request, 'inversiones/calculadora.html')

@login_required(login_url='login')
def estados_view(request):
    return render(request, 'inversiones/estados.html')

@login_required(login_url='login')
def pagos_view(request):
    return render(request, 'inversiones/pagos.html')

@login_required(login_url='login')
def promotores_view(request):
    return render(request, 'inversiones/promotores.html')

@login_required(login_url='login')
def prospectos_view(request):
    return render(request, 'inversiones/prospectos.html')


# ══════════════════════════════════════════════
#  INVERSIONISTAS API
# ══════════════════════════════════════════════

@api_view(['GET', 'POST'])
def inversionistas_list(request):
    """
    GET  /api/inversionistas/       — list all investors
    POST /api/inversionistas/       — create new investor
    """
    if request.method == 'GET':
        queryset = Inversionista.objects.all().order_by('nombre_completo')

        # Optional filters
        search = request.GET.get('search')
        if search:
            queryset = queryset.filter(nombre_completo__icontains=search)

        tipo = request.GET.get('tipo')
        if tipo:
            queryset = queryset.filter(tipo_contribuyente=tipo)

        serializer = InversionistaListSerializer(queryset, many=True)
        return Response(serializer.data)

    if request.method == 'POST':
        serializer = InversionistaSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
def inversionista_detail(request, pk):
    """
    GET    /api/inversionistas/<pk>/  — get single investor with all inversiones
    PUT    /api/inversionistas/<pk>/  — update investor
    DELETE /api/inversionistas/<pk>/  — delete investor
    """
    inversionista = get_object_or_404(Inversionista, pk=pk)

    if request.method == 'GET':
        serializer = InversionistaSerializer(inversionista)
        return Response(serializer.data)

    if request.method == 'PUT':
        serializer = InversionistaSerializer(inversionista, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        inversionista.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ══════════════════════════════════════════════
#  INVERSIONES API
# ══════════════════════════════════════════════

@api_view(['GET', 'POST'])
def inversiones_list(request):
    """
    GET  /api/inversiones/   — list all inversiones (filter by ?estado=activo etc.)
    POST /api/inversiones/   — create new inversion
    """
    if request.method == 'GET':
        queryset = Inversion.objects.select_related('inversionista').all()
        estado = request.GET.get('estado')
        if estado:
            queryset = queryset.filter(estado=estado)
        serializer = InversionSerializer(queryset, many=True)
        return Response(serializer.data)

    if request.method == 'POST':
        serializer = InversionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT'])
def inversion_detail(request, pk):
    inversion = get_object_or_404(Inversion, pk=pk)

    if request.method == 'GET':
        serializer = InversionSerializer(inversion)
        return Response(serializer.data)

    if request.method == 'PUT':
        serializer = InversionSerializer(inversion, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ══════════════════════════════════════════════
#  CALCULADORA API
# ══════════════════════════════════════════════

@api_view(['POST'])
def calcular_intereses(request):
    """
    POST /api/calculadora/
    Body: { capital, tasa_anual, dias, base, porcentaje_factura }
    Returns: full interest breakdown
    """
    serializer = CalculadoraInputSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    d = serializer.validated_data
    capital          = Decimal(str(d['capital']))
    tasa             = Decimal(str(d['tasa_anual'])) / Decimal('100')
    dias             = Decimal(str(d['dias']))
    base             = Decimal(str(d['base']))
    pct_factura      = Decimal(str(d['porcentaje_factura'])) / Decimal('100')
    pct_externo      = Decimal('1') - pct_factura

    # Formula
    interes_bruto    = capital * (tasa / base) * dias
    base_factura     = interes_bruto * pct_factura
    isr              = base_factura * Decimal('0.20')
    subtotal_factura = base_factura - isr
    iva              = subtotal_factura * Decimal('0.16')
    total_factura    = subtotal_factura + iva
    pago_externo     = interes_bruto * pct_externo
    total_pagar      = total_factura + pago_externo

    return Response({
        'capital':           str(capital.quantize(Decimal('0.01'))),
        'tasa_anual':        str(d['tasa_anual']),
        'dias':              d['dias'],
        'base':              d['base'],
        'porcentaje_factura': str(d['porcentaje_factura']),
        'porcentaje_externo': str(pct_externo * 100),
        'interes_bruto':     str(interes_bruto.quantize(Decimal('0.01'))),
        'base_factura':      str(base_factura.quantize(Decimal('0.01'))),
        'isr':               str(isr.quantize(Decimal('0.01'))),
        'subtotal_factura':  str(subtotal_factura.quantize(Decimal('0.01'))),
        'iva':               str(iva.quantize(Decimal('0.01'))),
        'total_factura':     str(total_factura.quantize(Decimal('0.01'))),
        'pago_externo':      str(pago_externo.quantize(Decimal('0.01'))),
        'total_pagar':       str(total_pagar.quantize(Decimal('0.01'))),
    })


# ══════════════════════════════════════════════
#  ESTADOS DE CUENTA API
# ══════════════════════════════════════════════

@api_view(['GET', 'POST'])
def estados_list(request):
    """
    GET  /api/estados/   — list all estados (filter by ?estado=pendiente)
    POST /api/estados/   — manually create a single estado
    """
    if request.method == 'GET':
        queryset = EstadoDeCuenta.objects.select_related(
            'inversion__inversionista'
        ).all().order_by('-fecha_generado')

        estado = request.GET.get('estado')
        if estado:
            queryset = queryset.filter(estado=estado)

        serializer = EstadoDeCuentaSerializer(queryset, many=True)
        return Response(serializer.data)

    if request.method == 'POST':
        serializer = EstadoDeCuentaSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT'])
def estado_detail(request, pk):
    estado = get_object_or_404(EstadoDeCuenta, pk=pk)

    if request.method == 'GET':
        serializer = EstadoDeCuentaSerializer(estado)
        return Response(serializer.data)

    if request.method == 'PUT':
        serializer = EstadoDeCuentaSerializer(estado, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def generar_estados_todos(request):
    """
    POST /api/estados/generar-todos/
    Generates monthly statements for ALL active inversiones
    that don't have a statement for the current month yet.
    Body: { periodo_inicio, periodo_fin, dias_periodo }
    """
    periodo_inicio = request.data.get('periodo_inicio')
    periodo_fin    = request.data.get('periodo_fin')
    dias_periodo   = request.data.get('dias_periodo', 28)

    if not periodo_inicio or not periodo_fin:
        return Response(
            {'error': 'Se requiere periodo_inicio y periodo_fin'},
            status=status.HTTP_400_BAD_REQUEST
        )

    inversiones = Inversion.objects.filter(estado='activo').select_related('inversionista')
    generados = []
    omitidos  = []

    for inv in inversiones:
        # Skip if already has a statement for this period
        already_exists = EstadoDeCuenta.objects.filter(
            inversion=inv,
            periodo_inicio=periodo_inicio
        ).exists()

        if already_exists:
            omitidos.append(inv.inversionista.nombre_completo)
            continue

        capital       = inv.capital
        tasa          = inv.tasa_anual / Decimal('100')
        base          = Decimal(str(inv.base_calculo))
        dias          = Decimal(str(dias_periodo))
        pct_factura   = inv.porcentaje_factura / Decimal('100')
        pct_externo   = Decimal('1') - pct_factura

        interes_bruto    = capital * (tasa / base) * dias
        base_factura     = interes_bruto * pct_factura
        isr              = base_factura * Decimal('0.20')
        subtotal_factura = base_factura - isr
        iva              = subtotal_factura * Decimal('0.16')
        total_factura    = subtotal_factura + iva
        pago_externo     = interes_bruto * pct_externo
        total_pagar      = total_factura + pago_externo

        estado = EstadoDeCuenta.objects.create(
            inversion=inv,
            periodo_inicio=periodo_inicio,
            periodo_fin=periodo_fin,
            dias_periodo=dias_periodo,
            interes_bruto=interes_bruto.quantize(Decimal('0.01')),
            isr=isr.quantize(Decimal('0.01')),
            iva=iva.quantize(Decimal('0.01')),
            interes_neto=(subtotal_factura + iva).quantize(Decimal('0.01')),
            pago_externo=pago_externo.quantize(Decimal('0.01')),
            total_pagar=total_pagar.quantize(Decimal('0.01')),
            estado='generado'
        )
        generados.append(inv.inversionista.nombre_completo)

    return Response({
        'generados': len(generados),
        'omitidos':  len(omitidos),
        'detalle_generados': generados,
        'detalle_omitidos':  omitidos,
    })


# ══════════════════════════════════════════════
#  PAGOS API
# ══════════════════════════════════════════════

@api_view(['GET'])
def pagos_list(request):
    """
    GET /api/pagos/  — list all pagos (filter by ?estado=pendiente&mes=2026-03)
    """
    queryset = Pago.objects.select_related(
        'estado_de_cuenta__inversion__inversionista'
    ).all().order_by('-estado_de_cuenta__periodo_inicio')

    estado = request.GET.get('estado')
    if estado:
        queryset = queryset.filter(estado=estado)

    serializer = PagoSerializer(queryset, many=True)
    return Response(serializer.data)


@api_view(['GET', 'PUT'])
def pago_detail(request, pk):
    pago = get_object_or_404(Pago, pk=pk)

    if request.method == 'GET':
        serializer = PagoSerializer(pago)
        return Response(serializer.data)

    if request.method == 'PUT':
        serializer = PagoSerializer(pago, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def marcar_pagado(request, pk):
    """
    POST /api/pagos/<pk>/marcar-pagado/
    Body: { fecha_pago, notas, confirmado_por }
    Marks a payment as paid and generates a folio number.
    """
    pago = get_object_or_404(Pago, pk=pk)

    if pago.estado == 'pagado':
        return Response(
            {'error': 'Este pago ya fue marcado como pagado'},
            status=status.HTTP_400_BAD_REQUEST
        )

    pago.estado         = 'pagado'
    pago.fecha_pago     = request.data.get('fecha_pago', timezone.now().date())
    pago.notas          = request.data.get('notas', '')
    pago.confirmado_por = request.data.get('confirmado_por', '')

    # Auto-generate folio
    if not pago.folio:
        year  = timezone.now().year
        count = Pago.objects.filter(estado='pagado').count() + 1
        pago.folio = f"RCP-{year}-{str(count).zfill(4)}"

    pago.save()
    serializer = PagoSerializer(pago)
    return Response(serializer.data)


# ══════════════════════════════════════════════
#  PROMOTORES API
# ══════════════════════════════════════════════

@api_view(['GET', 'POST'])
def promotores_list(request):
    if request.method == 'GET':
        queryset = Promotor.objects.all().order_by('nombre')
        serializer = PromotorSerializer(queryset, many=True)
        return Response(serializer.data)

    if request.method == 'POST':
        serializer = PromotorSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
def promotor_detail(request, pk):
    promotor = get_object_or_404(Promotor, pk=pk)

    if request.method == 'GET':
        serializer = PromotorSerializer(promotor)
        return Response(serializer.data)

    if request.method == 'PUT':
        serializer = PromotorSerializer(promotor, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        promotor.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ══════════════════════════════════════════════
#  PROSPECTOS API
# ══════════════════════════════════════════════

@api_view(['GET', 'POST'])
def prospectos_list(request):
    if request.method == 'GET':
        queryset = Prospecto.objects.filter(convertido=False).order_by('etapa', 'nombre_completo')
        etapa = request.GET.get('etapa')
        if etapa:
            queryset = queryset.filter(etapa=etapa)
        serializer = ProspectoSerializer(queryset, many=True)
        return Response(serializer.data)

    if request.method == 'POST':
        serializer = ProspectoSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
def prospecto_detail(request, pk):
    prospecto = get_object_or_404(Prospecto, pk=pk)

    if request.method == 'GET':
        serializer = ProspectoSerializer(prospecto)
        return Response(serializer.data)

    if request.method == 'PUT':
        serializer = ProspectoSerializer(prospecto, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        prospecto.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
def convertir_prospecto(request, pk):
    """
    POST /api/prospectos/<pk>/convertir/
    Converts a prospecto into a full Inversionista.
    Creates the Inversionista record and marks the prospecto as converted.
    """
    prospecto = get_object_or_404(Prospecto, pk=pk)

    if prospecto.convertido:
        return Response(
            {'error': 'Este prospecto ya fue convertido a inversionista'},
            status=status.HTTP_400_BAD_REQUEST
        )

    inversionista = Inversionista.objects.create(
        nombre_completo=prospecto.nombre_completo,
        correo=prospecto.correo,
        telefono=prospecto.telefono,
        promotor=prospecto.promotor,
    )

    prospecto.convertido     = True
    prospecto.inversionista  = inversionista
    prospecto.save()

    return Response({
        'message': f'{prospecto.nombre_completo} convertido a inversionista exitosamente.',
        'inversionista_id': inversionista.id,
    }, status=status.HTTP_201_CREATED)


# ══════════════════════════════════════════════
#  DASHBOARD SUMMARY API
# ══════════════════════════════════════════════

@api_view(['GET'])
def dashboard_summary(request):
    """
    GET /api/dashboard/
    Returns all metrics needed for the dashboard.
    """
    from django.utils import timezone
    from datetime import date, timedelta
    import calendar

    today = date.today()

    # ── Inversionistas ──
    total_inversionistas  = Inversionista.objects.count()
    inversiones_activas   = Inversion.objects.filter(estado='activo')
    inversiones_venciendo = Inversion.objects.filter(
        estado='activo',
        fecha_vencimiento__range=[today, today + timedelta(days=15)]
    )
    inversiones_vencidas  = Inversion.objects.filter(estado='vencido').count()

    # ── Capital ──
    capital_total = sum(i.capital for i in inversiones_activas) if inversiones_activas.exists() else 0

    # ── Estados de cuenta ──
    total_estados     = EstadoDeCuenta.objects.count()
    estados_generados = EstadoDeCuenta.objects.filter(estado='generado').count()
    estados_pendientes = EstadoDeCuenta.objects.filter(estado='pendiente').count()
    total_intereses   = sum(
        e.total_pagar for e in EstadoDeCuenta.objects.filter(
            periodo_inicio__year=today.year,
            periodo_inicio__month=today.month
        )
    ) if EstadoDeCuenta.objects.exists() else 0

    # ── Pagos ──
    pagos_pendientes = Pago.objects.filter(estado='pendiente').count()
    pagos_pagados    = Pago.objects.filter(estado='pagado').count()

    # ── Advertencias ──
    advertencias = []

    # Inversiones por vencer en 15 días
    for inv in inversiones_venciendo.select_related('inversionista')[:5]:
        dias_restantes = (inv.fecha_vencimiento - today).days
        advertencias.append({
            'tipo': 'por_vencer',
            'nombre': inv.inversionista.nombre_completo,
            'detalle': f'Vence en {dias_restantes} día{"s" if dias_restantes != 1 else ""}',
            'icono': 'calendar-x-fill',
            'color': 'red',
        })

    # Inversionistas sin RFC
    sin_rfc = Inversionista.objects.filter(rfc='').select_related()[:3]
    for inv in sin_rfc:
        advertencias.append({
            'tipo': 'datos_incompletos',
            'nombre': inv.nombre_completo,
            'detalle': 'Falta RFC',
            'icono': 'person-exclamation-fill',
            'color': 'red',
        })

    # Pagos pendientes como advertencia
    pagos_pend_list = Pago.objects.filter(
        estado='pendiente'
    ).select_related('estado_de_cuenta__inversion__inversionista')[:3]
    for p in pagos_pend_list:
        advertencias.append({
            'tipo': 'pago_pendiente',
            'nombre': p.estado_de_cuenta.inversion.inversionista.nombre_completo,
            'detalle': 'Pago pendiente de confirmación',
            'icono': 'credit-card-fill',
            'color': 'warning',
        })

    # ── Chart: last 8 months of total_pagar ──
    chart = []
    for i in range(7, -1, -1):
        d = today.replace(day=1) - timedelta(days=1)
        for _ in range(i):
            d = d.replace(day=1) - timedelta(days=1)
        month_total = sum(
            e.total_pagar for e in EstadoDeCuenta.objects.filter(
                periodo_inicio__year=d.year,
                periodo_inicio__month=d.month
            )
        )
        chart.append({
            'mes': calendar.month_abbr[d.month].capitalize(),
            'total': str(month_total),
        })

    return Response({
        'total_inversionistas':  total_inversionistas,
        'inversiones_activas':   inversiones_activas.count(),
        'inversiones_venciendo': inversiones_venciendo.count(),
        'inversiones_vencidas':  inversiones_vencidas,
        'capital_total':         str(capital_total),
        'total_intereses_mes':   str(total_intereses),
        'estados_generados':     estados_generados,
        'total_estados':         total_estados,
        'estados_pendientes':    estados_pendientes,
        'pagos_pendientes':      pagos_pendientes,
        'pagos_pagados':         pagos_pagados,
        'advertencias':          advertencias[:6],
        'chart':                 chart,
    })