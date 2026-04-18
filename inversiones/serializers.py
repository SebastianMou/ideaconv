from rest_framework import serializers
from .models import (
    Promotor, Inversionista, Inversion, Movimiento,
    EstadoDeCuenta, Pago, Prospecto
)

class PromotorSerializer(serializers.ModelSerializer):
    total_referidos = serializers.SerializerMethodField()
    capital_total = serializers.SerializerMethodField()

    class Meta:
        model = Promotor
        fields = '__all__'

    def get_total_referidos(self, obj):
        return obj.inversionistas.count()

    def get_capital_total(self, obj):
        total = sum(
            inv.capital
            for inv in obj.inversionistas.all()
            for inv in inv.inversiones.filter(estado='activo')
        )
        return total


class MovimientoSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)

    class Meta:
        model = Movimiento
        fields = '__all__'


class InversionSerializer(serializers.ModelSerializer):
    porcentaje_externo = serializers.ReadOnlyField()
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    base_display = serializers.CharField(source='get_base_calculo_display', read_only=True)
    movimientos = MovimientoSerializer(many=True, read_only=True)

    class Meta:
        model = Inversion
        fields = '__all__'

class InversionistaSerializer(serializers.ModelSerializer):
    promotor_nombre = serializers.CharField(source='promotor.nombre', read_only=True)
    inversiones = InversionSerializer(many=True, read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_contribuyente_display', read_only=True)
    estado_civil_display = serializers.CharField(source='get_estado_civil_display', read_only=True)
    documento_display = serializers.CharField(source='get_tipo_documento_display', read_only=True)
    banco_display = serializers.CharField(source='get_banco_display', read_only=True)

    class Meta:
        model = Inversionista
        fields = '__all__'


class InversionistaListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for the list view (no nested inversiones)."""
    promotor_nombre = serializers.CharField(source='promotor.nombre', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_contribuyente_display', read_only=True)
    inversion_activa = serializers.SerializerMethodField()

    class Meta:
        model = Inversionista
        fields = [
            'id', 'nombre_completo', 'rfc', 'tipo_contribuyente',
            'tipo_display', 'correo', 'telefono', 'promotor_nombre',
            'fecha_ingreso', 'inversion_activa', 'fecha_eliminado'
        ]

    def get_inversion_activa(self, obj):
        inv = obj.inversiones.filter(estado='activo').first()
        if inv:
            return {
                'id': inv.id,
                'capital': str(inv.capital),
                'tasa_anual': str(inv.tasa_anual),
                'estado': inv.estado,
                'porcentaje_factura': str(inv.porcentaje_factura),
            }
        return None


class EstadoDeCuentaSerializer(serializers.ModelSerializer):
    inversionista_nombre = serializers.SerializerMethodField()
    inversionista_rfc    = serializers.SerializerMethodField()
    estado_display       = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = EstadoDeCuenta
        fields = '__all__'

    def get_inversionista_nombre(self, obj):
        if obj.inversionista:
            return obj.inversionista.nombre_completo
        if obj.inversion:
            return obj.inversion.inversionista.nombre_completo
        return '—'

    def get_inversionista_rfc(self, obj):
        if obj.inversionista:
            return obj.inversionista.rfc
        if obj.inversion:
            return obj.inversion.inversionista.rfc
        return ''


class PagoSerializer(serializers.ModelSerializer):
    inversionista_nombre = serializers.SerializerMethodField()
    inversionista_rfc    = serializers.SerializerMethodField()
    metodo_display = serializers.CharField(source='get_metodo_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    total_pagar = serializers.DecimalField(
        source='estado_de_cuenta.total_pagar',
        max_digits=14, decimal_places=2, read_only=True
    )
    capital = serializers.SerializerMethodField()
    interes_neto = serializers.DecimalField(
        source='estado_de_cuenta.interes_neto',
        max_digits=14, decimal_places=2, read_only=True
    )
    pago_externo = serializers.DecimalField(
        source='estado_de_cuenta.pago_externo',
        max_digits=14, decimal_places=2, read_only=True
    )
    estado_de_cuenta_detalle = serializers.SerializerMethodField()

    class Meta:
        model = Pago
        fields = '__all__'

    def _get_inv(self, obj):
        edc = obj.estado_de_cuenta
        if edc.inversionista:
            return edc.inversionista
        if edc.inversion:
            return edc.inversion.inversionista
        return None

    def get_inversionista_nombre(self, obj):
        inv = self._get_inv(obj)
        return inv.nombre_completo if inv else '—'

    def get_inversionista_rfc(self, obj):
        inv = self._get_inv(obj)
        return inv.rfc if inv else ''

    def get_capital(self, obj):
        edc = obj.estado_de_cuenta
        if edc.inversion:
            return str(edc.inversion.capital)
        if edc.inversionista:
            total = sum(i.capital for i in edc.inversionista.inversiones.filter(estado='activo'))
            return str(total)
        return '0'

    def get_estado_de_cuenta_detalle(self, obj):
        edc = obj.estado_de_cuenta
        capital = self.get_capital(obj)
        tasa = '—'
        if edc.inversion:
            tasa = str(edc.inversion.tasa_anual)
        elif edc.inversionista:
            inv = edc.inversionista.inversiones.filter(estado='activo').first()
            if inv:
                tasa = str(inv.tasa_anual)
        return {
            'id':             edc.id,
            'periodo_inicio': str(edc.periodo_inicio),
            'periodo_fin':    str(edc.periodo_fin),
            'dias_periodo':   edc.dias_periodo,
            'interes_bruto':  str(edc.interes_bruto),
            'isr':            str(edc.isr),
            'iva':            str(edc.iva),
            'interes_neto':   str(edc.interes_neto),
            'pago_externo':   str(edc.pago_externo),
            'total_pagar':    str(edc.total_pagar),
            'capital':        capital,
            'tasa_anual':     tasa,
        }


class ProspectoSerializer(serializers.ModelSerializer):
    promotor_nombre = serializers.CharField(source='promotor.nombre', read_only=True)
    etapa_display = serializers.CharField(source='get_etapa_display', read_only=True)

    class Meta:
        model = Prospecto
        fields = '__all__'


# ── Calculator serializer (no model, just validates input) ──
class CalculadoraInputSerializer(serializers.Serializer):
    capital = serializers.DecimalField(max_digits=14, decimal_places=2)
    tasa_anual = serializers.DecimalField(max_digits=5, decimal_places=2)
    dias = serializers.IntegerField(min_value=1, max_value=366)
    base = serializers.ChoiceField(choices=[360, 365])
    porcentaje_factura = serializers.DecimalField(
        max_digits=10, decimal_places=6,
        min_value=0, max_value=100
    )