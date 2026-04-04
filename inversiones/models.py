from django.db import models
from django.db import models
from djrichtextfield.models import RichTextField

class HoneypotAttempt(models.Model):
    ip_address = models.GenericIPAddressField()
    username   = models.CharField(max_length=200, blank=True)
    timestamp  = models.DateTimeField(auto_now_add=True)
    user_agent = models.TextField(blank=True)

    def __str__(self):
        return f'{self.ip_address} — {self.username} — {self.timestamp}'

    class Meta:
        verbose_name = 'Intento de Acceso (Honeypot)'
        verbose_name_plural = 'Intentos de Acceso (Honeypot)'
        ordering = ['-timestamp']

class Promotor(models.Model):
    nombre = models.CharField(max_length=200)
    telefono = models.CharField(max_length=20, blank=True)
    correo = models.EmailField(blank=True)
    activo = models.BooleanField(default=True)
    fecha_registro = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Promotor"
        verbose_name_plural = "Promotores"


class Inversionista(models.Model):
    TIPO_CONTRIBUYENTE = [
        ('fisica', 'Persona Física'),
        ('moral', 'Persona Moral'),
    ]
    ESTADO_CIVIL = [
        ('soltero', 'Soltero(a)'),
        ('casado', 'Casado(a)'),
        ('divorciado', 'Divorciado(a)'),
        ('viudo', 'Viudo(a)'),
    ]
    TIPO_DOCUMENTO = [
        ('ine', 'INE / Credencial de Elector'),
        ('pasaporte', 'Pasaporte'),
        ('cedula', 'Cédula Profesional'),
        ('otro', 'Otro'),
    ]
    BANCO_CHOICES = [
        ('bbva', 'BBVA Bancomer'),
        ('banorte', 'Banorte'),
        ('hsbc', 'HSBC'),
        ('santander', 'Santander'),
        ('banamex', 'Banamex'),
        ('otro', 'Otro'),
    ]

    # Datos personales
    tipo_contribuyente = models.CharField(max_length=10, choices=TIPO_CONTRIBUYENTE, default='fisica')
    es_entidad_financiera = models.BooleanField(default=False)
    nombre_completo = models.CharField(max_length=300)
    nacionalidad = models.CharField(max_length=100, default='Mexicana')
    curp = models.CharField(max_length=18, blank=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    correo = models.EmailField(blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    fecha_ingreso = models.DateField(auto_now_add=True)
    tipo_documento = models.CharField(max_length=20, choices=TIPO_DOCUMENTO, default='ine')
    numero_documento = models.CharField(max_length=50, blank=True)
    estado_civil = models.CharField(max_length=15, choices=ESTADO_CIVIL, default='soltero')

    # Domicilio
    calle = models.CharField(max_length=300, blank=True)
    ciudad = models.CharField(max_length=100, blank=True)
    estado = models.CharField(max_length=100, blank=True)
    codigo_postal = models.CharField(max_length=10, blank=True)

    # Datos fiscales
    rfc = models.CharField(max_length=13, blank=True)
    regimen_fiscal = models.CharField(max_length=200, default='Régimen de Intereses')
    nombre_fiscal = models.CharField(max_length=300, blank=True)
    pais_fiscal = models.CharField(max_length=100, default='México')
    estado_fiscal = models.CharField(max_length=100, blank=True)
    cp_fiscal = models.CharField(max_length=10, blank=True)

    # Datos bancarios
    banco = models.CharField(max_length=20, choices=BANCO_CHOICES, blank=True)
    clabe = models.CharField(max_length=18, blank=True)

    # Red
    promotor = models.ForeignKey(
        Promotor, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='inversionistas'
    )

    def __str__(self):
        return self.nombre_completo

    class Meta:
        verbose_name = "Inversionista"
        verbose_name_plural = "Inversionistas"


class Inversion(models.Model):
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('por_vencer', 'Por Vencer'),
        ('vencido', 'Vencido'),
    ]
    BASE_CHOICES = [
        (365, '365 días'),
        (360, '360 días'),
    ]

    inversionista = models.ForeignKey(
        Inversionista, on_delete=models.CASCADE,
        related_name='inversiones'
    )
    capital = models.DecimalField(max_digits=14, decimal_places=2)
    tasa_anual = models.DecimalField(max_digits=5, decimal_places=2, help_text='Porcentaje, ej. 15.00')
    base_calculo = models.IntegerField(choices=BASE_CHOICES, default=365)
    porcentaje_factura = models.DecimalField(max_digits=5, decimal_places=2, default=100, help_text='% que se factura, el resto es pago externo')
    fecha_inicio = models.DateField()
    fecha_vencimiento = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='activo')
    notas = models.TextField(blank=True)

    @property
    def porcentaje_externo(self):
        return 100 - self.porcentaje_factura

    def __str__(self):
        return f"{self.inversionista.nombre_completo} — ${self.capital}"

    class Meta:
        verbose_name = "Inversión"
        verbose_name_plural = "Inversiones"


class EstadoDeCuenta(models.Model):
    ESTADO_CHOICES = [
        ('generado', 'Generado'),
        ('enviado', 'Enviado'),
        ('pendiente', 'Pendiente'),
    ]

    inversion = models.ForeignKey(
        Inversion, on_delete=models.CASCADE,
        related_name='estados_de_cuenta'
    )
    periodo_inicio = models.DateField()
    periodo_fin = models.DateField()
    dias_periodo = models.IntegerField()
    interes_bruto = models.DecimalField(max_digits=14, decimal_places=2)
    isr = models.DecimalField(max_digits=14, decimal_places=2)
    iva = models.DecimalField(max_digits=14, decimal_places=2)
    interes_neto = models.DecimalField(max_digits=14, decimal_places=2)
    pago_externo = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_pagar = models.DecimalField(max_digits=14, decimal_places=2)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='pendiente')
    fecha_generado = models.DateTimeField(auto_now_add=True)
    notas = models.TextField(blank=True)

    def __str__(self):
        return f"Estado {self.inversion.inversionista.nombre_completo} — {self.periodo_inicio}"

    class Meta:
        verbose_name = "Estado de Cuenta"
        verbose_name_plural = "Estados de Cuenta"


class Pago(models.Model):
    METODO_CHOICES = [
        ('transferencia', 'Transferencia bancaria'),
        ('efectivo', 'Efectivo'),
        ('sindicato', 'Sindicato'),
        ('otro', 'Otro'),
    ]
    ESTADO_CHOICES = [
        ('pagado', 'Pagado'),
        ('pendiente', 'Pendiente'),
    ]

    estado_de_cuenta = models.OneToOneField(
        EstadoDeCuenta, on_delete=models.CASCADE,
        related_name='pago'
    )
    metodo = models.CharField(max_length=20, choices=METODO_CHOICES)
    fecha_pago = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='pendiente')
    folio = models.CharField(max_length=30, blank=True)
    notas = models.TextField(blank=True)
    confirmado_por = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"Pago {self.folio} — {self.estado}"

    class Meta:
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"


class Prospecto(models.Model):
    ETAPA_CHOICES = [
        ('inicial', 'Contacto Inicial'),
        ('seguimiento', 'En Seguimiento'),
        ('listo', 'Listo para Alta'),
    ]

    nombre_completo = models.CharField(max_length=300)
    telefono = models.CharField(max_length=20, blank=True)
    correo = models.EmailField(blank=True)
    monto_estimado = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    promotor = models.ForeignKey(
        Promotor, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='prospectos'
    )
    etapa = models.CharField(max_length=15, choices=ETAPA_CHOICES, default='inicial')
    notas = models.TextField(blank=True)
    fecha_registro = models.DateField(auto_now_add=True)
    convertido = models.BooleanField(default=False)
    inversionista = models.OneToOneField(
        Inversionista, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='prospecto_origen'
    )

    def __str__(self):
        return self.nombre_completo

    class Meta:
        verbose_name = "Prospecto"
        verbose_name_plural = "Prospectos"

class BugReport(models.Model):
    TIPO_CHOICES = [
        ('calculo',    'Error en cálculo'),
        ('visual',     'Error visual / diseño'),
        ('formulario', 'Formulario no guarda'),
        ('email',      'Error en envío de correo'),
        ('carga',      'Página no carga / lenta'),
        ('otro',       'Otro'),
    ]
    tipo        = models.CharField(max_length=20, choices=TIPO_CHOICES)
    pagina      = models.CharField(max_length=200)
    descripcion = RichTextField()
    esperado    = RichTextField(blank=True)
    url_actual  = models.URLField(blank=True)
    usuario     = models.CharField(max_length=200, blank=True)
    fecha       = models.DateTimeField(auto_now_add=True)
    resuelto    = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.get_tipo_display()} — {self.pagina} — {self.fecha.strftime("%d/%m/%Y %H:%M")}'

    class Meta:
        verbose_name = 'Reporte de Error'
        verbose_name_plural = 'Reportes de Errores'
        ordering = ['-fecha']