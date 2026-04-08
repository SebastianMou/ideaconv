from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.core.mail import EmailMultiAlternatives
from django.conf import settings as django_settings

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

import logging
honeypot_logger = logging.getLogger('honeypot')

def honeypot_view(request):
    ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', 'unknown'))
    if request.method == 'POST':
        username   = request.POST.get('username', '')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        honeypot_logger.warning(f'HONEYPOT HIT — IP: {ip} | Username: {username}')
        from .models import HoneypotAttempt
        HoneypotAttempt.objects.create(
            ip_address=ip if ip != 'unknown' else '0.0.0.0',
            username=username,
            user_agent=user_agent,
        )
    from django.http import HttpResponse
    from django.middleware.csrf import get_token
    csrf_token = get_token(request)
    return HttpResponse(f"""<!DOCTYPE html><html><head><title>Log in | Django site admin</title>
    <style>
      body{{font-family:sans-serif;background:#f8f8f8;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;}}
      .login{{background:#fff;padding:40px;border-radius:4px;box-shadow:0 2px 8px rgba(0,0,0,.15);width:300px;}}
      h1{{font-size:18px;color:#333;margin-bottom:6px;}}
      .help{{font-size:13px;color:#666;margin-bottom:20px;}}
      .error{{background:#ffefef;border:1px solid #e0b4b4;color:#a94442;padding:8px 12px;border-radius:3px;font-size:13px;margin-bottom:16px;}}
      label{{font-size:13px;font-weight:bold;display:block;margin-bottom:4px;color:#333;}}
      input[type=text],input[type=password]{{width:100%;padding:8px;margin-bottom:14px;border:1px solid #ccc;border-radius:3px;box-sizing:border-box;font-size:14px;}}
      button{{width:100%;padding:10px;background:#79aec8;color:#fff;border:none;border-radius:3px;cursor:pointer;font-size:14px;font-weight:bold;}}
      button:hover{{background:#609ab6;}}
    </style></head>
    <body><div class="login">
      <h1>Administration</h1>
      <p class="help">Enter the correct username and password to access the admin.</p>
      <div class="error">Please enter the correct username and password for a staff account. Note that both fields may be case-sensitive.</div>
      <form method="post">
        <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">
        <label for="id_username">Username:</label>
        <input type="text" name="username" id="id_username" autocomplete="username">
        <label for="id_password">Password:</label>
        <input type="password" name="password" id="id_password" autocomplete="current-password">
        <button type="submit">Log in</button>
      </form>
    </div></body></html>""", status=200)

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

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username   = request.POST.get('username', '').strip()
        password1  = request.POST.get('password1', '')
        password2  = request.POST.get('password2', '')
        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name', '').strip()

        from django.contrib.auth.models import User

        if not username or not password1:
            return render(request, 'inversiones/register.html', {
                'error': 'Usuario y contraseña son obligatorios.',
                'username': username, 'first_name': first_name, 'last_name': last_name,
            })
        if password1 != password2:
            return render(request, 'inversiones/register.html', {
                'error': 'Las contraseñas no coinciden.',
                'username': username, 'first_name': first_name, 'last_name': last_name,
            })
        if len(password1) < 6:
            return render(request, 'inversiones/register.html', {
                'error': 'La contraseña debe tener al menos 6 caracteres.',
                'username': username, 'first_name': first_name, 'last_name': last_name,
            })
        if User.objects.filter(username=username).exists():
            return render(request, 'inversiones/register.html', {
                'error': f'El usuario "{username}" ya existe.',
                'username': username, 'first_name': first_name, 'last_name': last_name,
            })

        user = User.objects.create_user(
            username=username,
            password=password1,
            first_name=first_name,
            last_name=last_name,
        )
        login(request, user)
        return redirect('dashboard')

    return render(request, 'inversiones/register.html')

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
        queryset = Inversionista.objects.all().order_by('-id')

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
    iva              = base_factura * Decimal('0.16')
    total_factura    = base_factura - isr + iva
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
        iva              = base_factura * Decimal('0.16')
        total_factura    = base_factura - isr + iva
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
        fecha_vencimiento__range=[today, today + timedelta(days=60)]
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

    # Inversiones por vencer en 60 días (2 meses)
    for inv in inversiones_venciendo.select_related('inversionista').order_by('fecha_vencimiento')[:10]:
        dias_restantes = (inv.fecha_vencimiento - today).days
        if dias_restantes <= 7:
            urgencia = 'red'
            detalle  = f'⚠️ Vence en {dias_restantes} día{"s" if dias_restantes != 1 else ""} — URGENTE'
        elif dias_restantes <= 30:
            urgencia = 'red'
            detalle  = f'Vence en {dias_restantes} días ({inv.fecha_vencimiento.strftime("%d/%m/%Y")})'
        else:
            urgencia = 'warning'
            detalle  = f'Vence en {dias_restantes} días ({inv.fecha_vencimiento.strftime("%d/%m/%Y")})'
        advertencias.append({
            'tipo':   'por_vencer',
            'nombre': inv.inversionista.nombre_completo,
            'detalle': detalle,
            'icono':  'calendar-x-fill',
            'color':  urgencia,
            'capital': str(inv.capital),
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
        'venciendo_detalle':     advertencias[:10],
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

# ══════════════════════════════════════════════
#  EMAIL VIEWS
# ══════════════════════════════════════════════

@api_view(['GET'])
@login_required(login_url='login')
def estado_preview(request, pk):
    """
    GET /api/estados/<pk>/preview/
    Returns full estado de cuenta data for email preview/edit.
    """
    estado = get_object_or_404(EstadoDeCuenta, pk=pk)
    inv    = estado.inversion.inversionista
    return Response({
        'id':               estado.id,
        'inversionista':    inv.nombre_completo,
        'rfc':              inv.rfc or '',
        'correo':           inv.correo or '',
        'capital':          str(estado.inversion.capital),
        'tasa':             str(estado.inversion.tasa_anual),
        'periodo_inicio':   str(estado.periodo_inicio),
        'periodo_fin':      str(estado.periodo_fin),
        'dias_periodo':     estado.dias_periodo,
        'interes_bruto':    str(estado.interes_bruto),
        'isr':              str(estado.isr),
        'iva':              str(estado.iva),
        'interes_neto':     str(estado.interes_neto),
        'pago_externo':     str(estado.pago_externo),
        'total_pagar':      str(estado.total_pagar),
        'estado':           estado.estado,
        'notas':            estado.notas or '',
    })


def _build_email_html(data, notas_extra='', tipo_comprobante='ambos'):
    """Builds the HTML email body for an estado de cuenta."""
    notas_section = f'<p style="margin-top:16px;padding:10px 14px;background:#FFF9E6;border-radius:8px;font-size:13px;color:#666;">📝 <strong>Notas:</strong> {notas_extra}</p>' if notas_extra else ''
    
    bruto   = float(data['interes_bruto'])
    isr     = float(data['isr'])
    iva     = float(data['iva'])
    externo = float(data['pago_externo'])
    neto    = float(data['interes_neto'])
    total   = float(data['total_pagar'])

    show_fact = tipo_comprobante in ('ambos', 'factura')
    show_ext  = tipo_comprobante in ('ambos', 'externo')

    fact_rows = f"""
      <tr><td colspan="2" style="padding:8px 14px;font-size:10px;font-weight:700;text-transform:uppercase;color:#C8282A;background:#FFF5F5;">Con Factura</td></tr>
      <tr style="background:#F4F6FA;"><td style="padding:10px 14px;color:#6B7A99;">Interés base factura</td><td style="padding:10px 14px;font-weight:700;text-align:right;">${bruto - externo:,.2f}</td></tr>
      <tr><td style="padding:10px 14px;color:#C8282A;">ISR (20%)</td><td style="padding:10px 14px;font-weight:700;text-align:right;color:#C8282A;">– ${isr:,.2f}</td></tr>
      <tr style="background:#F4F6FA;"><td style="padding:10px 14px;color:#1CB87E;">IVA (16%)</td><td style="padding:10px 14px;font-weight:700;text-align:right;color:#1CB87E;">+ ${iva:,.2f}</td></tr>
    """ if show_fact and (bruto - externo) > 0 else ''

    ext_rows = f"""
      <tr><td colspan="2" style="padding:8px 14px;font-size:10px;font-weight:700;text-transform:uppercase;color:#6B7A99;background:#F8F9FB;">Sin Factura (Pago Externo)</td></tr>
      <tr><td style="padding:10px 14px;color:#6B7A99;">Pago externo</td><td style="padding:10px 14px;font-weight:700;text-align:right;">${externo:,.2f}</td></tr>
      <tr style="background:#F4F6FA;"><td style="padding:10px 14px;color:#6B7A99;">ISR / IVA</td><td style="padding:10px 14px;text-align:right;color:#6B7A99;">No aplica</td></tr>
    """ if show_ext and externo > 0 else ''

    total_mostrar = neto if tipo_comprobante == 'factura' else externo if tipo_comprobante == 'externo' else total

    total_row = f'${total_mostrar:,.2f}'

    return f"""
    <div style="font-family:Arial,sans-serif;max-width:540px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.1);">
      <div style="background:#1A2340;padding:28px 32px;">
        <div style="font-size:22px;font-weight:800;color:#fff;letter-spacing:1px;">IDEACONV</div>
        <div style="font-size:13px;color:rgba(255,255,255,.5);margin-top:4px;">Estado de Cuenta Mensual</div>
      </div>
      <div style="padding:28px 32px;">
        <p style="font-size:15px;color:#1A2340;margin-bottom:4px;">Estimado(a) <strong>{data['inversionista']}</strong>,</p>
        <p style="font-size:13px;color:#6B7A99;margin-bottom:24px;">Le compartimos el resumen de su inversión correspondiente al período <strong>{data['periodo_inicio']} al {data['periodo_fin']}</strong>.</p>

        <table style="width:100%;border-collapse:collapse;font-size:13.5px;">
          <tr style="background:#F4F6FA;">
            <td style="padding:10px 14px;color:#6B7A99;">Capital invertido</td>
            <td style="padding:10px 14px;font-weight:700;text-align:right;">${float(data['capital']):,.2f}</td>
          </tr>
          <tr>
            <td style="padding:10px 14px;color:#6B7A99;">Tasa anual</td>
            <td style="padding:10px 14px;font-weight:700;text-align:right;">{data['tasa']}%</td>
          </tr>
          <tr style="background:#F4F6FA;">
            <td style="padding:10px 14px;color:#6B7A99;">Días del período</td>
            <td style="padding:10px 14px;font-weight:700;text-align:right;">{data['dias_periodo']} días</td>
          </tr>
          <tr>
            <td style="padding:10px 14px;color:#6B7A99;">Interés bruto</td>
            <td style="padding:10px 14px;font-weight:700;text-align:right;">${float(data['interes_bruto']):,.2f}</td>
          </tr>
          <tr style="background:#F4F6FA;">
            <td style="padding:10px 14px;color:#C8282A;">Retención ISR (20%)</td>
            <td style="padding:10px 14px;font-weight:700;text-align:right;color:#C8282A;">– ${float(data['isr']):,.2f}</td>
          </tr>
          <tr>
            <td style="padding:10px 14px;color:#1CB87E;">IVA (16%)</td>
            <td style="padding:10px 14px;font-weight:700;text-align:right;color:#1CB87E;">+ ${float(data['iva']):,.2f}</td>
          </tr>
            {fact_rows}
            {ext_rows}
        </table>

        <table style="width:100%;border-collapse:collapse;background:#1A2340;border-radius:10px;margin-top:16px;">
          <tr>
            <td style="padding:16px 20px;color:rgba(255,255,255,.7);font-weight:600;font-size:13.5px;">TOTAL A PAGAR</td>
            <td style="padding:16px 20px;color:#fff;font-weight:800;font-size:20px;text-align:right;">{total_row}</td>
          </tr>
        </table>

        {notas_section}

        <p style="margin-top:24px;font-size:12px;color:#9AA5BE;border-top:1px solid #E2E8F0;padding-top:16px;">
          Este es un documento interno de Ideaconv S.A. de C.V. — {data['periodo_inicio']} al {data['periodo_fin']}
        </p>
      </div>
    </div>
    """


@api_view(['POST'])
@login_required(login_url='login')
def estado_enviar(request, pk):
    """
    POST /api/estados/<pk>/enviar/
    Body: { correo (optional override), asunto (optional), notas_extra (optional) }
    Sends the estado de cuenta email to the investor.
    """
    estado = get_object_or_404(EstadoDeCuenta, pk=pk)
    inv    = estado.inversion.inversionista

    correo_destino = request.data.get('correo') or inv.correo
    asunto         = request.data.get('asunto') or f'Estado de Cuenta — {estado.periodo_inicio} al {estado.periodo_fin}'
    notas_extra        = request.data.get('notas_extra', '')
    tipo_comprobante   = request.data.get('tipo_comprobante', 'ambos')

    if not correo_destino:
        return Response(
            {'error': f'{inv.nombre_completo} no tiene correo registrado.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    data = {
        'inversionista': inv.nombre_completo,
        'rfc':           inv.rfc or '',
        'capital':       str(estado.inversion.capital),
        'tasa':          str(estado.inversion.tasa_anual),
        'periodo_inicio': str(estado.periodo_inicio),
        'periodo_fin':    str(estado.periodo_fin),
        'dias_periodo':   estado.dias_periodo,
        'interes_bruto':  str(estado.interes_bruto),
        'isr':            str(estado.isr),
        'iva':            str(estado.iva),
        'interes_neto':   str(estado.interes_neto),
        'pago_externo':   str(estado.pago_externo),
        'total_pagar':    str(estado.total_pagar),
    }

    html_content = _build_email_html(data, notas_extra, tipo_comprobante)
    text_content = f"Estado de Cuenta de {inv.nombre_completo} — Total a pagar: ${float(estado.total_pagar):,.2f}"

    try:
        msg = EmailMultiAlternatives(
            subject=asunto,
            body=text_content,
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            to=[correo_destino],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()

        # Mark as sent
        estado.estado = 'enviado'
        estado.save()

        return Response({'message': f'Correo enviado a {correo_destino} exitosamente.'})

    except Exception as e:
        return Response(
            {'error': f'Error al enviar correo: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@login_required(login_url='login')
def enviar_estados_todos(request):
    """
    POST /api/estados/enviar-todos/
    Sends emails to all investors with generado estados de cuenta.
    Body: { asunto (optional), notas_extra (optional) }
    """
    asunto      = request.data.get('asunto', 'Estado de Cuenta Mensual — Ideaconv')
    notas_extra = request.data.get('notas_extra', '')

    estados = EstadoDeCuenta.objects.filter(
        estado='generado'
    ).select_related('inversion__inversionista')

    enviados  = []
    fallidos  = []
    sin_correo = []

    for estado in estados:
        inv = estado.inversion.inversionista
        if not inv.correo:
            sin_correo.append(inv.nombre_completo)
            continue

        data = {
            'inversionista': inv.nombre_completo,
            'rfc':           inv.rfc or '',
            'capital':       str(estado.inversion.capital),
            'tasa':          str(estado.inversion.tasa_anual),
            'periodo_inicio': str(estado.periodo_inicio),
            'periodo_fin':    str(estado.periodo_fin),
            'dias_periodo':   estado.dias_periodo,
            'interes_bruto':  str(estado.interes_bruto),
            'isr':            str(estado.isr),
            'iva':            str(estado.iva),
            'interes_neto':   str(estado.interes_neto),
            'pago_externo':   str(estado.pago_externo),
            'total_pagar':    str(estado.total_pagar),
        }
        html_content = _build_email_html(data, notas_extra)
        text_content = f"Estado de Cuenta — Total a pagar: ${float(estado.total_pagar):,.2f}"

        try:
            msg = EmailMultiAlternatives(
                subject=asunto,
                body=text_content,
                from_email=django_settings.DEFAULT_FROM_EMAIL,
                to=[inv.correo],
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            estado.estado = 'enviado'
            estado.save()
            enviados.append(inv.nombre_completo)
        except Exception as e:
            fallidos.append({'nombre': inv.nombre_completo, 'error': str(e)})

    return Response({
        'enviados':    len(enviados),
        'fallidos':    len(fallidos),
        'sin_correo':  len(sin_correo),
        'detalle_enviados':   enviados,
        'detalle_fallidos':   fallidos,
        'detalle_sin_correo': sin_correo,
    })

@api_view(['POST'])
@login_required(login_url='login')
def bug_report(request):
    from .models import BugReport
    BugReport.objects.create(
        tipo        = request.data.get('tipo', ''),
        pagina      = request.data.get('pagina', ''),
        descripcion = request.data.get('descripcion', ''),
        esperado    = request.data.get('esperado', ''),
        url_actual  = request.data.get('url_actual', ''),
        usuario     = request.data.get('usuario', ''),
    )
    return Response({'message': 'Reporte recibido'}, status=status.HTTP_201_CREATED)