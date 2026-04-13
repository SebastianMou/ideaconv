from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import request, status
from django.core.mail import EmailMultiAlternatives
from django.conf import settings as django_settings
from io import BytesIO
from reportlab.platypus import Image as RLImage
from urllib.request import urlopen
from io import BytesIO as BIO

from .models import (
    Promotor, Inversionista, Inversion, Movimiento,
    EstadoDeCuenta, Pago, Prospecto
)
from .serializers import (
    PromotorSerializer, InversionistaSerializer, InversionistaListSerializer,
    InversionSerializer, EstadoDeCuentaSerializer, PagoSerializer,
    ProspectoSerializer, CalculadoraInputSerializer, MovimientoSerializer
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


@api_view(['GET', 'PUT', 'DELETE'])
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

    if request.method == 'DELETE':
        inversion.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['GET', 'POST'])
def movimientos_list(request, inversion_pk):
    """
    GET  /api/inversiones/<pk>/movimientos/  — list movements for an investment
    POST /api/inversiones/<pk>/movimientos/  — add a new movement
    """
    inversion = get_object_or_404(Inversion, pk=inversion_pk)

    if request.method == 'GET':
        movimientos = inversion.movimientos.all().order_by('fecha')
        serializer  = MovimientoSerializer(movimientos, many=True)
        return Response(serializer.data)

    if request.method == 'POST':
        data = request.data.copy()
        data['inversion'] = inversion_pk
        serializer = MovimientoSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            # Update inversion.capital to reflect new balance
            mov = serializer.instance
            if mov.tipo == 'abono':
                inversion.capital += mov.monto
            else:
                inversion.capital -= mov.monto
            inversion.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
def movimiento_detail(request, pk):
    """
    DELETE /api/movimientos/<pk>/  — remove a movement and reverse its effect on capital
    """
    mov       = get_object_or_404(Movimiento, pk=pk)
    inversion = mov.inversion
    # Reverse the capital change
    if mov.tipo == 'abono':
        inversion.capital -= mov.monto
    else:
        inversion.capital += mov.monto
    inversion.save()
    mov.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)

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
            estado = serializer.save()
            Pago.objects.create(
                estado_de_cuenta=estado,
                metodo='transferencia',
                estado='pendiente',
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
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

    if request.method == 'DELETE':
        estado.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
def generar_estados_todos(request):
    """
    POST /api/estados/generar-todos/
    Generates ONE EstadoDeCuenta per investor (consolidating all their
    active inversiones) for the given period.
    Body: { periodo_inicio, periodo_fin, dias_periodo }
    """
    periodo_inicio = request.data.get('periodo_inicio')
    periodo_fin    = request.data.get('periodo_fin')
    dias_periodo   = int(request.data.get('dias_periodo', 28))

    if not periodo_inicio or not periodo_fin:
        return Response(
            {'error': 'Se requiere periodo_inicio y periodo_fin'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Get all investors that have at least one active investment
    inversionistas = Inversionista.objects.filter(
        inversiones__estado='activo'
    ).distinct()

    generados = []
    omitidos  = []

    for inversionista in inversionistas:
        # Skip if already has a consolidated estado for this period
        already_exists = EstadoDeCuenta.objects.filter(
            inversionista=inversionista,
            periodo_inicio=periodo_inicio
        ).exists()

        if already_exists:
            omitidos.append(inversionista.nombre_completo)
            continue

        inversiones_activas = inversionista.inversiones.filter(estado='activo')

        # Sum across all investments using tranche calculation
        total_bruto   = Decimal('0')
        total_isr     = Decimal('0')
        total_iva     = Decimal('0')
        total_externo = Decimal('0')

        for inv in inversiones_activas:
            pct_factura = inv.porcentaje_factura / Decimal('100')
            pct_externo = Decimal('1') - pct_factura

            bruto_inv    = _calcular_interes_con_movimientos(inv, periodo_inicio, periodo_fin)
            fact_inv     = bruto_inv * pct_factura
            isr_inv      = fact_inv * Decimal('0.20')
            iva_inv      = fact_inv * Decimal('0.16')
            externo_inv  = bruto_inv * pct_externo

            total_bruto   += bruto_inv
            total_isr     += isr_inv
            total_iva     += iva_inv
            total_externo += externo_inv

        subtotal_fact = (total_bruto - total_externo) - total_isr
        total_fact    = subtotal_fact + total_iva
        interes_neto  = subtotal_fact + total_iva
        total_pagar   = total_fact + total_externo

        EstadoDeCuenta.objects.create(
            inversionista=inversionista,
            inversion=None,
            periodo_inicio=periodo_inicio,
            periodo_fin=periodo_fin,
            dias_periodo=dias_periodo,
            interes_bruto=total_bruto.quantize(Decimal('0.01')),
            isr=total_isr.quantize(Decimal('0.01')),
            iva=total_iva.quantize(Decimal('0.01')),
            interes_neto=interes_neto.quantize(Decimal('0.01')),
            pago_externo=total_externo.quantize(Decimal('0.01')),
            total_pagar=total_pagar.quantize(Decimal('0.01')),
            estado='generado'
        )
        generados.append(inversionista.nombre_completo)

    return Response({
        'generados': len(generados),
        'omitidos':  len(omitidos),
        'detalle_generados': generados,
        'detalle_omitidos':  omitidos,
    })


def _calcular_interes_con_movimientos(inversion, periodo_inicio, periodo_fin):
    """
    Calculates interest for a period using pro-rated tranches.
    Each deposit (abono) or withdrawal (retiro) splits the period.
    Returns interes_bruto as Decimal.
    """
    from datetime import date, timedelta

    p_inicio = periodo_inicio if isinstance(periodo_inicio, date) else date.fromisoformat(str(periodo_inicio))
    p_fin    = periodo_fin    if isinstance(periodo_fin,    date) else date.fromisoformat(str(periodo_fin))

    tasa = inversion.tasa_anual / Decimal('100')
    base = Decimal(str(inversion.base_calculo))

    # Get all movements within the period, sorted by date
    movimientos = inversion.movimientos.filter(
        fecha__gte=p_inicio,
        fecha__lte=p_fin
    ).order_by('fecha')

    # Build tranches: list of (capital, start_date, end_date)
    tranches = []
    capital_actual = inversion.capital
    tranche_start  = p_inicio

    for mov in movimientos:
        # Close current tranche on movement date
        if mov.fecha > tranche_start:
            tranches.append((capital_actual, tranche_start, mov.fecha))
        # Apply movement
        if mov.tipo == 'abono':
            capital_actual += mov.monto
        else:  # retiro
            capital_actual -= mov.monto
        tranche_start = mov.fecha

    # Final tranche from last movement to period end
    end_exclusive = p_fin + timedelta(days=1)
    if tranche_start < end_exclusive:
        tranches.append((capital_actual, tranche_start, end_exclusive))

    # Sum interest across all tranches
    interes_bruto = Decimal('0')
    for capital_t, start_t, end_t in tranches:
        dias_t = Decimal(str((end_t - start_t).days))
        if dias_t > 0 and capital_t > 0:
            interes_bruto += capital_t * (tasa / base) * dias_t

    return interes_bruto.quantize(Decimal('0.01'))

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


@api_view(['GET', 'PUT', 'DELETE'])
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

    if request.method == 'DELETE':
        pago.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


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



# ══════════════════════════════════════════════════════════════
#  PDF BUILDER  —  replace / add this function in views.py
# ══════════════════════════════════════════════════════════════
 
def _build_estado_pdf(data):
    """
    Builds a PDF Estado de Cuenta that mirrors the Ideaconv PDF format.
 
    `data` dict must contain everything _build_email_html uses, PLUS:
        data['curp']           str   — investor CURP (blank OK)
        data['calle']          str   — street address
        data['ciudad']         str
        data['estado_dir']     str   — state (named estado_dir to avoid clash with estado de cuenta)
        data['codigo_postal']  str
        data['inversiones']    list  — each item:
            {
              'folio':            str,
              'capital':          str,
              'tasa_anual':       str,
              'base_calculo':     int,
              'fecha_inicio':     str,
              'fecha_vencimiento':str,
              'dias':             int,   # days in this period
              'interes_bruto':    str,
              'retencion':        str,   # ISR amount, '0.00' if N/A
              'iva_inv':          str,   # IVA amount, '0.00' if N/A
              'interes_neto':     str,
            }
    Returns: bytes  (the raw PDF)
    """
    from io import BytesIO
    from datetime import datetime
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer,
        Table, TableStyle, HRFlowable,
    )
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
 
    # ── Brand colours ──
    NAVY       = colors.HexColor('#1A2340')
    RED        = colors.HexColor('#C8282A')
    GRAY       = colors.HexColor('#6B7A99')
    BGBLUE     = colors.HexColor('#1A5276')
    ROWBG      = colors.HexColor('#F4F6FA')
    WHITE      = colors.white
    BORDER     = colors.HexColor('#E2E8F0')
    LIGHT_BLUE = colors.HexColor('#AED6F1')
 
    # ── Quick style factory ──
    def S(name, **kw):
        p = ParagraphStyle(name)
        for k, v in kw.items():
            setattr(p, k, v)
        return p
 
    fmt = lambda v: '${:,.2f}'.format(float(v))
 
    # ── Derive month label from periodo_fin ──
    MESES = ['Enero','Febrero','Marzo','Abril','Mayo','Junio',
             'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
    try:
        d = datetime.strptime(data['periodo_fin'], '%Y-%m-%d')
        mes_nombre = MESES[d.month - 1] + ' ' + str(d.year)
    except Exception:
        mes_nombre = data['periodo_fin']
 
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
        leftMargin=0.6*inch, rightMargin=0.6*inch,
        topMargin=0.5*inch,  bottomMargin=0.6*inch)
 
    story = []
 
    # ════════════════════════════════
    #  HEADER  — investor info + logo
    # ════════════════════════════════
    inv_lines = [
        Paragraph('<b>' + data['inversionista'] + '</b>',
                  S('ih', fontName='Helvetica-Bold', fontSize=9, textColor=NAVY)),
        Paragraph('RFC: ' + (data.get('rfc') or 'N/A'),
                  S('ir', fontName='Helvetica', fontSize=8, textColor=GRAY)),
    ]
    if data.get('curp'):
        inv_lines.append(Paragraph('CURP: ' + data['curp'],
                  S('ic', fontName='Helvetica', fontSize=8, textColor=GRAY)))
    if data.get('calle'):
        inv_lines.append(Paragraph('CALLE: ' + data['calle'],
                  S('ia', fontName='Helvetica', fontSize=8, textColor=GRAY)))
    city_line = ' '.join(filter(None, [
        data.get('ciudad',''),
        'C.P ' + data.get('codigo_postal','') if data.get('codigo_postal') else '',
        data.get('estado_dir',''),
    ]))
    if city_line.strip():
        inv_lines.append(Paragraph(city_line,
                  S('il', fontName='Helvetica', fontSize=8, textColor=GRAY, leading=11)))
 
    LOGO_URL = 'https://res.cloudinary.com/dgzhlipft/image/upload/q_auto/f_auto/v1775856062/logo_ideacon_1000x431_nretqf.png'
    try:
        logo_data = BIO(urlopen(LOGO_URL).read())
        logo_img  = RLImage(logo_data, width=1.6*inch, height=0.69*inch)  # keeps 1000x431 ratio
        logo_el   = logo_img
    except Exception:
        logo_el = Paragraph('<b>IDEACONV</b>',
                  S('lo', fontName='Helvetica-Bold', fontSize=20, textColor=NAVY, alignment=TA_RIGHT))

    logo_lines = [
        logo_el,
        Spacer(1, 6),
        Paragraph('¡El poder de querer...!', S('lt', fontName='Helvetica-Oblique', fontSize=9, textColor=RED, alignment=TA_RIGHT)),
        Spacer(1, 4),
        Paragraph('Mes de corte: ' + mes_nombre, S('lm', fontName='Helvetica', fontSize=8, textColor=GRAY, alignment=TA_RIGHT)),
    ]
 
    header_tbl = Table([[inv_lines, logo_lines]], colWidths=[3.8*inch, 3.2*inch])
    header_tbl.setStyle(TableStyle([
        ('VALIGN',        (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING',   (0,0), (-1,-1), 0),
        ('RIGHTPADDING',  (0,0), (-1,-1), 0),
        ('TOPPADDING',    (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width='100%', thickness=1, color=BORDER))
    story.append(Spacer(1, 12))
 
    # ════════════════════════════════
    #  TITLE
    # ════════════════════════════════
    story.append(Paragraph(
        'ESTADO DE CUENTA ' + mes_nombre.upper(),
        S('title', fontName='Helvetica-Bold', fontSize=14, textColor=NAVY, alignment=TA_CENTER)
    ))
    story.append(Spacer(1, 14))
 
    # ════════════════════════════════
    #  KPI SUMMARY BOXES
    # ════════════════════════════════
    kpi_val_s = S('kv', fontName='Helvetica-Bold', fontSize=14, textColor=WHITE,  alignment=TA_CENTER)
    kpi_lbl_s = S('kl', fontName='Helvetica',      fontSize=8,  textColor=LIGHT_BLUE, alignment=TA_CENTER)
 
    kpi_tbl = Table([
        [Paragraph(fmt(data['capital']),       kpi_val_s),
         Paragraph(fmt(data['interes_bruto']), kpi_val_s),
         Paragraph(fmt(data['total_pagar']),   kpi_val_s)],
        [Paragraph('Monto capital',   kpi_lbl_s),
         Paragraph('Interés Bruto',   kpi_lbl_s),
         Paragraph('Interés a Pagar', kpi_lbl_s)],
    ], colWidths=[2.33*inch]*3)
    kpi_tbl.setStyle(TableStyle([
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [BGBLUE, colors.HexColor('#154360')]),
        ('TOPPADDING',     (0,0), (-1,-1), 10),
        ('BOTTOMPADDING',  (0,0), (-1,-1), 10),
        ('GRID',           (0,0), (-1,-1), 0.5, colors.HexColor('#2E86C1')),
    ]))
    story.append(kpi_tbl)
    story.append(Spacer(1, 16))
 
    # ════════════════════════════════
    #  PAGARÉ BREAKDOWN TABLE
    # ════════════════════════════════
    # Section header bar
    story.append(Table(
        [[Paragraph('Desglose de Pagarés en MXN del mes',
            S('dh', fontName='Helvetica-Bold', fontSize=9, textColor=WHITE, alignment=TA_CENTER))]],
        colWidths=[7.0*inch],
        style=TableStyle([
            ('BACKGROUND',    (0,0), (-1,-1), BGBLUE),
            ('TOPPADDING',    (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('LEFTPADDING',   (0,0), (-1,-1), 6),
        ])
    ))
    story.append(Spacer(1, 1))
 
    hdr_s = S('ch', fontName='Helvetica-Bold', fontSize=8, textColor=WHITE, alignment=TA_CENTER)
    val_s = S('cv', fontName='Helvetica',      fontSize=8, textColor=NAVY,  alignment=TA_CENTER)
    vbl_s = S('cb', fontName='Helvetica-Bold', fontSize=8, textColor=NAVY,  alignment=TA_CENTER)
    tot_s = S('ct', fontName='Helvetica-Bold', fontSize=8, textColor=WHITE, alignment=TA_CENTER)
 
    col_w = [0.65*inch, 1.1*inch, 0.5*inch, 1.0*inch, 0.9*inch, 0.7*inch, 0.55*inch, 0.9*inch]
    hdrs  = ['#Pagaré', 'Capital', 'Plazo', 'Tasa Bruta Anual',
             'Interés Bruto', 'Retención', 'IVA', 'Interés Neto']
 
    rows = [[Paragraph(h, hdr_s) for h in hdrs]]
    totals = {'bruto': 0.0, 'ret': 0.0, 'iva': 0.0, 'neto': 0.0}
 
    for inv in data.get('inversiones', []):
        b  = float(inv['interes_bruto'])
        r  = float(inv.get('retencion', 0))
        iv = float(inv.get('iva_inv', 0))
        n  = float(inv['interes_neto'])
        totals['bruto'] += b
        totals['ret']   += r
        totals['iva']   += iv
        totals['neto']  += n
        rows.append([
            Paragraph(inv['folio'],         vbl_s),
            Paragraph(fmt(inv['capital']),  val_s),
            Paragraph(str(inv['dias']),     val_s),
            Paragraph(str(inv['tasa_anual']) + ' %', val_s),
            Paragraph(fmt(inv['interes_bruto']), val_s),
            Paragraph('-' if r  == 0 else fmt(r),  val_s),
            Paragraph('-' if iv == 0 else fmt(iv), val_s),
            Paragraph(fmt(inv['interes_neto']), vbl_s),
        ])
 
    rows.append([
        Paragraph('Total:', tot_s),
        Paragraph('',                       tot_s),
        Paragraph('',                       tot_s),
        Paragraph('',                       tot_s),
        Paragraph(fmt(totals['bruto']),     tot_s),
        Paragraph(fmt(totals['ret']),       tot_s),
        Paragraph(fmt(totals['iva']),       tot_s),
        Paragraph(fmt(totals['neto']),      tot_s),
    ])
 
    breakdown = Table(rows, colWidths=col_w)
    breakdown.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),  (-1,0),  BGBLUE),
        ('BACKGROUND',    (0,-1), (-1,-1), BGBLUE),
        ('ROWBACKGROUNDS',(0,1),  (-1,-2), [WHITE, ROWBG]),
        ('GRID',          (0,0),  (-1,-1), 0.5, BORDER),
        ('VALIGN',        (0,0),  (-1,-1), 'MIDDLE'),
        ('TOPPADDING',    (0,0),  (-1,-1), 6),
        ('BOTTOMPADDING', (0,0),  (-1,-1), 6),
    ]))
    story.append(breakdown)
    story.append(Spacer(1, 28))
 
    # ════════════════════════════════
    #  FOOTER
    # ════════════════════════════════
    story.append(HRFlowable(width='100%', thickness=0.5, color=BORDER))
    story.append(Spacer(1, 6))
    footer_tbl = Table([[
        Paragraph('Ignacio López Rayón No. 385\nCol. Centro\nC.P. 64000 Monterrey, Nuevo León',
                  S('ft',  fontName='Helvetica', fontSize=7, textColor=GRAY, leading=11)),
        Paragraph('IDEACONV S.A. de C.V.',
                  S('ft2', fontName='Helvetica-Bold', fontSize=7, textColor=NAVY, alignment=TA_RIGHT)),
    ]], colWidths=[3.5*inch, 3.5*inch])
    footer_tbl.setStyle(TableStyle([
        ('VALIGN',        (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING',   (0,0), (-1,-1), 0),
        ('RIGHTPADDING',  (0,0), (-1,-1), 0),
        ('TOPPADDING',    (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    
    story.append(footer_tbl)

    # ════════════════════════════════
    #  DETAIL PAGES — one per investment
    # ════════════════════════════════
    from reportlab.platypus import PageBreak

    for inv in data.get('inversiones', []):
        story.append(PageBreak())

        # Investment header
        inv_hdr_data = [
            [Paragraph('<b>' + data['inversionista'] + '</b>',
                S('dih', fontName='Helvetica-Bold', fontSize=9, textColor=NAVY)),
             Paragraph('', S('x'))],
        ]

        left_lines = [
            Paragraph('<b>FOLIO: ' + inv['folio'] + '</b>',
                S('fl', fontName='Helvetica-Bold', fontSize=9, textColor=NAVY)),
            Paragraph('Divisa: MXN',
                S('fd', fontName='Helvetica', fontSize=8, textColor=GRAY)),
            Paragraph('Inversion inicial: $' + '{:,.2f}'.format(float(inv['capital'])) + ' MXN',
                S('fi', fontName='Helvetica', fontSize=8, textColor=GRAY)),
            Paragraph('Fecha de Inicio: ' + inv['fecha_inicio'],
                S('fs', fontName='Helvetica', fontSize=8, textColor=GRAY)),
            Paragraph('Fecha de Vencimiento: ' + inv['fecha_vencimiento'],
                S('fv', fontName='Helvetica', fontSize=8, textColor=GRAY)),
            Paragraph('Dia de corte: Ultimo dia del mes',
                S('fc', fontName='Helvetica', fontSize=8, textColor=GRAY)),
        ]
        right_lines = [
            Paragraph('Interes Anual Bruto: ' + str(inv['tasa_anual']) + ' %',
                S('ri', fontName='Helvetica', fontSize=8, textColor=GRAY, alignment=TA_RIGHT)),
            Paragraph('Tasa de Retencion: 20.0 %',
                S('rr', fontName='Helvetica', fontSize=8, textColor=GRAY, alignment=TA_RIGHT)),
            Paragraph('IVA: 16.0 %',
                S('rv', fontName='Helvetica', fontSize=8, textColor=GRAY, alignment=TA_RIGHT)),
            Paragraph('Tipo de Pago de Intereses: Simple',
                S('rt', fontName='Helvetica', fontSize=8, textColor=GRAY, alignment=TA_RIGHT)),
        ]

        detail_hdr = Table([[left_lines, right_lines]], colWidths=[3.5*inch, 3.5*inch])
        detail_hdr.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ]))

        # Re-add top investor name
        story.append(Paragraph('<b>' + data['inversionista'] + '</b>',
            S('dn', fontName='Helvetica-Bold', fontSize=9, textColor=NAVY)))
        story.append(Paragraph(data.get('rfc', ''),
            S('dr', fontName='Helvetica', fontSize=8, textColor=GRAY)))
        story.append(Spacer(1, 10))
        story.append(detail_hdr)
        story.append(Spacer(1, 16))

        # Detail table header
        story.append(Table(
            [[Paragraph('Detalle de operaciones ' + inv['folio'],
                S('dth', fontName='Helvetica-Bold', fontSize=9, textColor=WHITE, alignment=TA_CENTER))]],
            colWidths=[7.0*inch],
            style=TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), BGBLUE),
                ('TOPPADDING', (0,0), (-1,-1), 8),
                ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ])
        ))
        story.append(Spacer(1, 1))

        dhdr_s = S('dhd', fontName='Helvetica-Bold', fontSize=8, textColor=WHITE, alignment=TA_CENTER)
        dval_s = S('dvl', fontName='Helvetica', fontSize=8, textColor=NAVY, alignment=TA_CENTER)
        dvbl_s = S('dvb', fontName='Helvetica-Bold', fontSize=8, textColor=NAVY, alignment=TA_CENTER)
        dtot_s = S('dtt', fontName='Helvetica-Bold', fontSize=8, textColor=WHITE, alignment=TA_CENTER)
        dlft_s = S('dlf', fontName='Helvetica', fontSize=8, textColor=NAVY, alignment=TA_LEFT)
        dlbl_s = S('dlb', fontName='Helvetica-Bold', fontSize=8, textColor=NAVY, alignment=TA_LEFT)

        dcol_w = [0.85*inch, 0.6*inch, 1.1*inch, 1.2*inch, 0.95*inch, 0.85*inch, 0.65*inch, 0.8*inch]
        dhdrs  = ['Fecha', 'Plazo', 'Monto', 'Concepto', 'Interes Bruto', 'Retencion', 'IVA', 'Interes Neto']

        drows = [[Paragraph(h, dhdr_s) for h in dhdrs]]

        # Capital inicial row
        drows.append([
            Paragraph(inv['fecha_inicio'], dval_s),
            Paragraph('', dval_s),
            Paragraph('$' + '{:,.2f}'.format(float(inv['capital'])), dvbl_s),
            Paragraph('Capital Inicial', dlbl_s),
            Paragraph('-', dval_s),
            Paragraph('-', dval_s),
            Paragraph('-', dval_s),
            Paragraph('-', dval_s),
        ])

        # Historical payment rows
        d_bruto_total = 0.0
        d_ret_total   = 0.0
        d_iva_total   = 0.0
        d_neto_total  = 0.0

        for hist in inv.get('estados_historicos', []):
            b = float(hist['interes_bruto'])
            r = float(hist['isr'])
            v = float(hist['iva'])
            n = float(hist['interes_neto'])
            d_bruto_total += b
            d_ret_total   += r
            d_iva_total   += v
            d_neto_total  += n
            drows.append([
                Paragraph(hist['periodo_fin'], dval_s),
                Paragraph(str(hist['dias_periodo']), dval_s),
                Paragraph('-', dval_s),
                Paragraph('Pago de Intereses', dlft_s),
                Paragraph('$' + '{:,.2f}'.format(b), dval_s),
                Paragraph('$' + '{:,.2f}'.format(r) if r > 0 else '-', dval_s),
                Paragraph('$' + '{:,.2f}'.format(v) if v > 0 else '-', dval_s),
                Paragraph('$' + '{:,.2f}'.format(n), dvbl_s),
            ])

            # Insert movements on their date if any match this period
            for mov in inv.get('movimientos', []):
                if hist['periodo_inicio'] <= mov['fecha'] <= hist['periodo_fin']:
                    drows.append([
                        Paragraph(mov['fecha'], dval_s),
                        Paragraph('', dval_s),
                        Paragraph('$' + '{:,.2f}'.format(float(mov['monto'])), dvbl_s),
                        Paragraph(mov['tipo_display'] + ' a Capital', dlft_s),
                        Paragraph('-', dval_s),
                        Paragraph('-', dval_s),
                        Paragraph('-', dval_s),
                        Paragraph('-', dval_s),
                    ])

        # Total row
        drows.append([
            Paragraph('Total', dtot_s),
            Paragraph('', dtot_s),
            Paragraph('$' + '{:,.2f}'.format(float(inv['capital'])), dtot_s),
            Paragraph('', dtot_s),
            Paragraph('$' + '{:,.2f}'.format(d_bruto_total), dtot_s),
            Paragraph('$' + '{:,.2f}'.format(d_ret_total),   dtot_s),
            Paragraph('$' + '{:,.2f}'.format(d_iva_total),   dtot_s),
            Paragraph('$' + '{:,.2f}'.format(d_neto_total),  dtot_s),
        ])

        detail_tbl = Table(drows, colWidths=dcol_w)
        detail_tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0,0),  (-1,0),  BGBLUE),
            ('BACKGROUND',    (0,-1), (-1,-1), BGBLUE),
            ('ROWBACKGROUNDS',(0,1),  (-1,-2), [WHITE, ROWBG]),
            ('GRID',          (0,0),  (-1,-1), 0.5, BORDER),
            ('VALIGN',        (0,0),  (-1,-1), 'MIDDLE'),
            ('TOPPADDING',    (0,0),  (-1,-1), 5),
            ('BOTTOMPADDING', (0,0),  (-1,-1), 5),
        ]))
        story.append(detail_tbl)
        story.append(Spacer(1, 20))

        # Footer on detail page
        story.append(HRFlowable(width='100%', thickness=0.5, color=BORDER))
        story.append(Spacer(1, 4))
        story.append(footer_tbl)

    doc.build(story)
    return buf.getvalue()
 
 
# ══════════════════════════════════════════════════════════════
#  EMAIL HTML BUILDER  — replace the existing _build_email_html
# ══════════════════════════════════════════════════════════════
 
def _build_email_html(data, notas_extra='', tipo_comprobante='ambos'):
    """
    Clean notification-style HTML email.
    All financial detail lives in the PDF attachment — this email is just
    a branded greeting card that tells the investor to check the PDF.
    """
    from datetime import datetime
 
    MESES = ['enero','febrero','marzo','abril','mayo','junio',
             'julio','agosto','septiembre','octubre','noviembre','diciembre']
    try:
        d = datetime.strptime(data['periodo_fin'], '%Y-%m-%d')
        fecha_display = f"{d.day} de {MESES[d.month-1]} de {d.year}"
    except Exception:
        fecha_display = data['periodo_fin']
 
    notas_row = ''
    if notas_extra:
        notas_row = f"""
        <tr>
          <td style="padding:0 32px 20px;">
            <div style="background:#FFF9E6;border-radius:8px;padding:12px 16px;
                        font-size:13px;color:#666;border:1px solid #FFE58F;">
              <b>Nota:</b> {notas_extra}
            </div>
          </td>
        </tr>"""
 
    return f"""<!DOCTYPE html>
        <html lang="es">
        <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
        <body style="margin:0;padding:0;background:#F5E6E6;font-family:Arial,sans-serif;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background:#F5E6E6;padding:24px 0;">
        <tr><td align="center">
        <table width="480" cellpadding="0" cellspacing="0"
                style="max-width:480px;width:100%;background:#fff;border-radius:10px;
                        overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.10);">
        
            <!-- TOP BAR -->
            <tr>
            <td style="background:#fff;padding:12px 20px;border-bottom:1px solid #e8e8e8;">
                <table width="100%" cellpadding="0" cellspacing="0"><tr>
                <td style="font-size:13px;font-weight:700;color:#1A2340;">Notificacion</td>
                <td align="right">
                    <img src="https://res.cloudinary.com/dgzhlipft/image/upload/q_auto/f_auto/v1775856062/logo_ideacon_1000x431_nretqf.png"
                        alt="IDEACONV" height="32" style="display:block;height:32px;width:auto;">
                </td>
                </tr></table>
            </td>
            </tr>

            <!-- HERO BANNER -->
            <tr>
            <td style="background:#C8282A;padding:40px 32px 36px;text-align:center;">
                <div style="width:64px;height:64px;background:rgba(255,255,255,.15);border-radius:14px;
                            margin:0 auto 20px;font-size:30px;line-height:64px;text-align:center;">&#128196;</div>
                <div style="font-size:22px;font-weight:800;color:#fff;margin-bottom:8px;">
                Estado de Cuenta</div>
                <div style="font-size:13px;color:rgba(255,255,255,.65);">{fecha_display}</div>
            </td>
            </tr>
        
            <!-- GREETING -->
            <tr>
            <td style="padding:28px 32px 8px;">
                <p style="margin:0 0 10px;font-size:14px;font-weight:700;color:#1A2340;">
                Estimado {data['inversionista']},</p>
                <p style="margin:0;font-size:13px;color:#555;line-height:1.6;">
                Gracias por su confianza. Adjunto encontrara su estado de cuenta
                correspondiente al periodo
                <b>{data['periodo_inicio']} al {data['periodo_fin']}</b>.</p>
            </td>
            </tr>
        
            {notas_row}
        
            <!-- PDF NOTICE -->
            <tr>
            <td style="padding:0 32px 24px;">
                <div style="background:#FFF0F0;border-radius:8px;padding:11px 14px;
                    font-size:12px;color:#C8282A;border:1px solid #F5C6C6;">
                    &#128206; <b>Adjunto:</b> Estado de cuenta con desglose completo en formato PDF.
                    </div>
            </td>
            </tr>
        
            <!-- FOOTER -->
            <tr>
            <td style="background:#f7f8fa;border-top:1px solid #e8e8e8;padding:20px 32px;">
                <table width="100%" cellpadding="0" cellspacing="0"><tr>
                <td valign="top">
                    <p style="margin:0 0 4px;font-size:11.5px;color:#888;">
                    Para dudas, no responder a este correo.</p>
                    <p style="margin:0 0 4px;font-size:11.5px;color:#888;">
                    Favor de oprimir el boton de AYUDA.</p>
                    <p style="margin:0 0 10px;font-size:11.5px;color:#888;">
                    Agreganos a tu lista de correos seguros:</p>
                    <p style="margin:0 0 10px;">
                    <a href="mailto:ideacon@ideaconv.com.mx"
                        style="font-size:11.5px;color:#1A5276;text-decoration:none;">
                        ideacon@ideaconv.com.mx</a></p>
                    <p style="margin:0 0 2px;">
                    <a href="#" style="font-size:11px;color:#888;text-decoration:underline;">
                        Consulta Nuestro Aviso de Privacidad</a></p>
                    <p style="margin:0;">
                    <a href="#" style="font-size:11px;color:#888;text-decoration:underline;">
                        Consulta Terminos y Condiciones</a></p>
                </td>
                <td align="right" valign="top" width="90">
                   <img src="https://res.cloudinary.com/dgzhlipft/image/upload/q_auto/f_auto/v1775856062/logo_ideacon_1000x431_nretqf.png" alt="IDEACONV" height="24" style="display:block;height:24px;width:auto;">
                </td>
                </tr></table>
            </td>
            </tr>
        
        </table>
        </td></tr>
        </table>
        </body>
        </html>
    """
 
 
# ══════════════════════════════════════════════════════════════════════════════
#  estado_enviar  — replace your existing view with this
# ══════════════════════════════════════════════════════════════════════════════
 
@api_view(['POST'])
@login_required(login_url='login')
def estado_enviar(request, pk):
    """
    POST /api/estados/<pk>/enviar/
    Sends ONE consolidated email + PDF per investor covering ALL their investments.
    """
    from io import BytesIO

    estado = get_object_or_404(EstadoDeCuenta, pk=pk)

    # Resolve the investor — works for both old (inversion FK) and new (inversionista FK) records
    if estado.inversionista:
        inv_obj = estado.inversionista
    else:
        inv_obj = estado.inversion.inversionista

    correo_destino   = request.data.get('correo') or inv_obj.correo
    asunto           = request.data.get('asunto') or \
        f'Estado de Cuenta — {estado.periodo_inicio} al {estado.periodo_fin}'
    notas_extra      = request.data.get('notas_extra', '')
    tipo_comprobante = request.data.get('tipo_comprobante', 'ambos')

    if not correo_destino:
        return Response(
            {'error': f'{inv_obj.nombre_completo} no tiene correo registrado.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Build the shared data dict
    data = {
        'inversionista':  inv_obj.nombre_completo,
        'rfc':            inv_obj.rfc or '',
        'curp':           getattr(inv_obj, 'curp', '') or '',
        'calle':          getattr(inv_obj, 'calle', '') or '',
        'ciudad':         getattr(inv_obj, 'ciudad', '') or '',
        'estado_dir':     getattr(inv_obj, 'estado', '') or '',
        'codigo_postal':  getattr(inv_obj, 'codigo_postal', '') or '',
        'capital':        str(estado.interes_bruto),  # shown as context in email
        'tasa':           '—',
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

    # Build per-investment rows — summary page (page 1)
    inversiones_activas = inv_obj.inversiones.filter(estado='activo').order_by('id')
    total_capital = sum(inv.capital for inv in inversiones_activas)
    data['capital'] = str(total_capital)

    inversiones_pdf = []
    for inversion in inversiones_activas:
        dias     = estado.dias_periodo
        pct_fact = float(inversion.porcentaje_factura) / 100
        bruto_i  = float(_calcular_interes_con_movimientos(
            inversion, estado.periodo_inicio, estado.periodo_fin
        ))
        fact_i   = bruto_i * pct_fact
        isr_i    = fact_i * 0.20
        iva_i    = fact_i * 0.16
        neto_i   = fact_i - isr_i + iva_i + (bruto_i * (1 - pct_fact))

        inversiones_pdf.append({
            'folio':             f'INV-{inversion.id}',
            'capital':           str(inversion.capital),
            'tasa_anual':        str(inversion.tasa_anual),
            'base_calculo':      inversion.base_calculo,
            'fecha_inicio':      str(inversion.fecha_inicio),
            'fecha_vencimiento': str(inversion.fecha_vencimiento) if inversion.fecha_vencimiento else 'Sin vencimiento',
            'dias':              dias,
            'interes_bruto':     f'{bruto_i:.2f}',
            'retencion':         f'{isr_i:.2f}',
            'iva_inv':           f'{iva_i:.2f}',
            'interes_neto':      f'{neto_i:.2f}',
            # Full history for detail pages
            'movimientos': [
                {
                    'fecha': str(m.fecha),
                    'monto': str(m.monto),
                    'tipo':  m.tipo,
                    'tipo_display': m.get_tipo_display(),
                }
                for m in inversion.movimientos.order_by('fecha')
            ],
            'estados_historicos': [
                {
                    'periodo_inicio': str(e.periodo_inicio),
                    'periodo_fin':    str(e.periodo_fin),
                    'dias_periodo':   e.dias_periodo,
                    'interes_bruto':  str(e.interes_bruto),
                    'isr':            str(e.isr),
                    'iva':            str(e.iva),
                    'interes_neto':   str(e.interes_neto),
                }
                for e in EstadoDeCuenta.objects.filter(
                    inversionista=inv_obj
                ).order_by('periodo_inicio')
            ],
        })

    data['inversiones'] = inversiones_pdf

    html_content = _build_email_html(data, notas_extra, tipo_comprobante)
    text_content = (
        f"Estado de Cuenta de {inv_obj.nombre_completo} — "
        f"Total a pagar: ${float(estado.total_pagar):,.2f}"
    )
    pdf_bytes    = _build_estado_pdf(data)
    pdf_filename = (
        f"estado-cuenta-{inv_obj.nombre_completo.replace(' ', '-').lower()}"
        f"-{estado.periodo_fin}.pdf"
    )

    try:
        msg = EmailMultiAlternatives(
            subject=asunto,
            body=text_content,
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            to=[correo_destino],
        )
        msg.attach_alternative(html_content, 'text/html')
        msg.attach(pdf_filename, pdf_bytes, 'application/pdf')
        msg.send()

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
    Sends ONE consolidated email per investor for all their generado estados.
    Groups multiple estados by investor and sends a single email each.
    """
    asunto      = request.data.get('asunto', 'Estado de Cuenta Mensual — Ideaconv')
    notas_extra = request.data.get('notas_extra', '')

    # Get all generado estados, grouped by investor
    estados = EstadoDeCuenta.objects.filter(
        estado='generado'
    ).select_related('inversionista', 'inversion__inversionista')

    # Group by investor
    from collections import defaultdict
    por_inversionista = defaultdict(list)
    for estado in estados:
        inv_obj = estado.inversionista or estado.inversion.inversionista
        por_inversionista[inv_obj.id].append((inv_obj, estado))

    enviados   = []
    fallidos   = []
    sin_correo = []

    for inv_id, items in por_inversionista.items():
        inv_obj = items[0][0]
        # Use the most recent estado for totals
        estado  = items[-1][1]

        if not inv_obj.correo:
            sin_correo.append(inv_obj.nombre_completo)
            continue

        data = {
            'inversionista':  inv_obj.nombre_completo,
            'rfc':            inv_obj.rfc or '',
            'curp':           getattr(inv_obj, 'curp', '') or '',
            'calle':          getattr(inv_obj, 'calle', '') or '',
            'ciudad':         getattr(inv_obj, 'ciudad', '') or '',
            'estado_dir':     getattr(inv_obj, 'estado', '') or '',
            'codigo_postal':  getattr(inv_obj, 'codigo_postal', '') or '',
            'tasa':           '—',
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

        inversiones_activas = inv_obj.inversiones.filter(estado='activo').order_by('id')
        total_capital = sum(inv.capital for inv in inversiones_activas)
        data['capital'] = str(total_capital)

        inversiones_pdf = []
        for inversion in inversiones_activas:
            dias     = estado.dias_periodo
            pct_fact = float(inversion.porcentaje_factura) / 100
            bruto_i  = float(_calcular_interes_con_movimientos(
                inversion, estado.periodo_inicio, estado.periodo_fin
            ))
            fact_i = bruto_i * pct_fact
            isr_i  = fact_i * 0.20
            iva_i  = fact_i * 0.16
            neto_i = fact_i - isr_i + iva_i + (bruto_i * (1 - pct_fact))

            inversiones_pdf.append({
                'folio':             f'INV-{inversion.id}',
                'capital':           str(inversion.capital),
                'tasa_anual':        str(inversion.tasa_anual),
                'base_calculo':      inversion.base_calculo,
                'fecha_inicio':      str(inversion.fecha_inicio),
                'fecha_vencimiento': str(inversion.fecha_vencimiento) if inversion.fecha_vencimiento else 'Sin vencimiento',
                'dias':              dias,
                'interes_bruto':     f'{bruto_i:.2f}',
                'retencion':         f'{isr_i:.2f}',
                'iva_inv':           f'{iva_i:.2f}',
                'interes_neto':      f'{neto_i:.2f}',
                'movimientos': [
                    {'fecha': str(m.fecha), 'monto': str(m.monto),
                     'tipo': m.tipo, 'tipo_display': m.get_tipo_display()}
                    for m in inversion.movimientos.order_by('fecha')
                ],
                'estados_historicos': [
                    {'periodo_inicio': str(e.periodo_inicio),
                     'periodo_fin':    str(e.periodo_fin),
                     'dias_periodo':   e.dias_periodo,
                     'interes_bruto':  str(e.interes_bruto),
                     'isr':            str(e.isr),
                     'iva':            str(e.iva),
                     'interes_neto':   str(e.interes_neto)}
                    for e in EstadoDeCuenta.objects.filter(
                        inversionista=inv_obj
                    ).order_by('periodo_inicio')
                ],
            })
        data['inversiones'] = inversiones_pdf

        html_content = _build_email_html(data, notas_extra)
        text_content = f"Estado de Cuenta — {inv_obj.nombre_completo}"
        pdf_bytes    = _build_estado_pdf(data)
        pdf_filename = (
            f"estado-cuenta-{inv_obj.nombre_completo.replace(' ','-').lower()}"
            f"-{estado.periodo_fin}.pdf"
        )

        try:
            msg = EmailMultiAlternatives(
                subject=asunto, body=text_content,
                from_email=django_settings.DEFAULT_FROM_EMAIL,
                to=[inv_obj.correo],
            )
            msg.attach_alternative(html_content, 'text/html')
            msg.attach(pdf_filename, pdf_bytes, 'application/pdf')
            msg.send()

            # Mark all this investor's estados as enviado
            for _, e in items:
                e.estado = 'enviado'
                e.save()

            enviados.append(inv_obj.nombre_completo)
        except Exception as e:
            fallidos.append({'nombre': inv_obj.nombre_completo, 'error': str(e)})

    return Response({
        'enviados':   len(enviados),
        'fallidos':   len(fallidos),
        'sin_correo': len(sin_correo),
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