from django.contrib import admin
from .models import (
    Promotor, Inversionista, Inversion,
    EstadoDeCuenta, Pago, Prospecto
)
from .models import HoneypotAttempt

@admin.register(HoneypotAttempt)
class HoneypotAttemptAdmin(admin.ModelAdmin):
    list_display  = ('ip_address', 'username', 'timestamp', 'user_agent')
    readonly_fields = ('ip_address', 'username', 'timestamp', 'user_agent')
    list_filter   = ('timestamp',)
    search_fields = ('ip_address', 'username')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Promotor)
class PromotorAdmin(admin.ModelAdmin):
    list_display  = ('nombre', 'telefono', 'correo', 'activo', 'fecha_registro')
    list_filter   = ('activo',)
    search_fields = ('nombre', 'correo')


class InversionInline(admin.TabularInline):
    model  = Inversion
    extra  = 0
    fields = ('capital', 'tasa_anual', 'base_calculo', 'porcentaje_factura', 'estado', 'fecha_inicio')


@admin.register(Inversionista)
class InversionistaAdmin(admin.ModelAdmin):
    list_display  = ('nombre_completo', 'rfc', 'tipo_contribuyente', 'correo', 'telefono', 'promotor')
    list_filter   = ('tipo_contribuyente', 'es_entidad_financiera', 'promotor')
    search_fields = ('nombre_completo', 'rfc', 'curp', 'correo')
    inlines       = [InversionInline]
    fieldsets = (
        ('Datos Personales', {
            'fields': (
                'tipo_contribuyente', 'es_entidad_financiera', 'nombre_completo',
                'nacionalidad', 'curp', 'fecha_nacimiento', 'estado_civil',
                'tipo_documento', 'numero_documento',
            )
        }),
        ('Contacto', {
            'fields': ('correo', 'telefono', 'calle', 'ciudad', 'estado', 'codigo_postal')
        }),
        ('Datos Fiscales', {
            'fields': (
                'rfc', 'regimen_fiscal', 'nombre_fiscal',
                'pais_fiscal', 'estado_fiscal', 'cp_fiscal',
            )
        }),
        ('Banco', {
            'fields': ('banco', 'clabe')
        }),
        ('Red', {
            'fields': ('promotor',)
        }),
    )


@admin.register(Inversion)
class InversionAdmin(admin.ModelAdmin):
    list_display  = ('inversionista', 'capital', 'tasa_anual', 'base_calculo', 'porcentaje_factura', 'estado', 'fecha_inicio')
    list_filter   = ('estado', 'base_calculo')
    search_fields = ('inversionista__nombre_completo',)


class PagoInline(admin.TabularInline):
    model  = Pago
    extra  = 0
    fields = ('metodo', 'estado', 'fecha_pago', 'folio', 'confirmado_por')


@admin.register(EstadoDeCuenta)
class EstadoDeCuentaAdmin(admin.ModelAdmin):
    list_display  = ('inversion', 'periodo_inicio', 'periodo_fin', 'total_pagar', 'estado', 'fecha_generado')
    list_filter   = ('estado',)
    search_fields = ('inversion__inversionista__nombre_completo',)
    inlines       = [PagoInline]


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display  = ('folio', 'estado_de_cuenta', 'metodo', 'estado', 'fecha_pago', 'confirmado_por')
    list_filter   = ('estado', 'metodo')
    search_fields = ('folio', 'estado_de_cuenta__inversion__inversionista__nombre_completo')


@admin.register(Prospecto)
class ProspectoAdmin(admin.ModelAdmin):
    list_display  = ('nombre_completo', 'telefono', 'monto_estimado', 'etapa', 'promotor', 'convertido', 'fecha_registro')
    list_filter   = ('etapa', 'convertido', 'promotor')
    search_fields = ('nombre_completo', 'correo')