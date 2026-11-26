# Project map: ideaconv

_Generated 2026-11-24 16:28 by project_map.py. 21 Python files (80 functions/methods), 0 JS files (0 functions/methods). Line numbers are shown as L<n>. Migrations excluded._

## File tree

```text
ideaconv/
├── core/
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── inversiones/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── serializers.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── backup_all.py
├── check_promotores.py
├── diagnostico_saldos.py
├── fix_factura_5decimals.py
├── manage.py
├── migrate_investors_standalone.py
├── reconstruir_estados.py
└── transform_only.py
```

## Python

### `backup_all.py`
_(no classes or functions)_

### `check_promotores.py`
_(no classes or functions)_

### `core/__init__.py`
_(no classes or functions)_

### `core/asgi.py`
_(no classes or functions)_

### `core/settings.py`
_(no classes or functions)_

### `core/urls.py`
- **URL patterns:**
  - `path('admin/', inv_views.honeypot_view, name='honeypot')` (L24)
  - `path('secure-ideaconv-panel/', admin.site.urls)` (L25)
  - `path('djrichtextfield/', include('djrichtextfield.urls'))` (L26)
  - `path('', include('inversiones.urls'))` (L27)

### `core/wsgi.py`
_(no classes or functions)_

### `diagnostico_saldos.py`
- **def** `norm(s)` (L17) — Uppercase, quita acentos y colapsa espacios — para emparejar nombres.

### `fix_factura_5decimals.py`
_(no classes or functions)_

### `inversiones/__init__.py`
_(no classes or functions)_

### `inversiones/admin.py`
- `@admin.register(HoneypotAttempt)` **class** `HoneypotAttemptAdmin(admin.ModelAdmin)` (L10)
  - `search_fields = ('ip_address', 'username')`
  - **def** `has_add_permission(self, request)` (L16)
  - **def** `has_change_permission(self, request, obj=None)` (L19)
- `@admin.register(Promotor)` **class** `PromotorAdmin(admin.ModelAdmin)` (L24)
  - `search_fields = ('nombre', 'correo')`
- **class** `InversionInline(admin.TabularInline)` (L30)
  - `model = Inversion`
  - `fields = ('capital', 'tasa_anual', 'base_calculo', 'porcentaje_factura', 'estado', 'fecha_inicio', 'fecha_...`
- `@admin.register(Inversionista)` **class** `InversionistaAdmin(admin.ModelAdmin)` (L37)
  - `search_fields = ('nombre_completo', 'rfc', 'curp', 'correo')`
  - **def** `restaurar_seleccionados(self, request, queryset)` (L71)
- `@admin.register(Inversion)` **class** `InversionAdmin(admin.ModelAdmin)` (L77)
  - `search_fields = ('inversionista__nombre_completo',)`
- **class** `PagoInline(admin.TabularInline)` (L83)
  - `model = Pago`
  - `fields = ('metodo', 'estado', 'fecha_pago', 'folio', 'confirmado_por')`
- `@admin.register(EstadoDeCuenta)` **class** `EstadoDeCuentaAdmin(admin.ModelAdmin)` (L90)
  - `search_fields = ('inversion__inversionista__nombre_completo',)`
- `@admin.register(Pago)` **class** `PagoAdmin(admin.ModelAdmin)` (L98)
  - `search_fields = ('folio', 'estado_de_cuenta__inversion__inversionista__nombre_completo')`
- `@admin.register(Prospecto)` **class** `ProspectoAdmin(admin.ModelAdmin)` (L105)
  - `search_fields = ('nombre_completo', 'correo')`
- `@admin.register(BugReport)` **class** `BugReportAdmin(admin.ModelAdmin)` (L111)
  - `search_fields = ('descripcion', 'pagina', 'usuario')`
  - `fields = ('tipo', 'pagina', 'descripcion', 'esperado', 'url_actual', 'usuario', 'fecha', 'resuelto')`

### `inversiones/apps.py`
- **class** `InversionesConfig(AppConfig)` (L4)
  - `name = 'inversiones'`

### `inversiones/models.py`
- **class** `HoneypotAttempt(models.Model)` (L5)
  - `ip_address = models.GenericIPAddressField()`
  - `username = models.CharField(max_length=200, blank=True)`
  - `timestamp = models.DateTimeField(auto_now_add=True)`
  - `user_agent = models.TextField(blank=True)`
  - **def** `__str__(self)` (L11)
  - **class** `Meta` (L14)
    - `verbose_name = 'Intento de Acceso (Honeypot)'`
    - `ordering = ['-timestamp']`
- **class** `Promotor(models.Model)` (L19)
  - `nombre = models.CharField(max_length=200)`
  - `telefono = models.CharField(max_length=20, blank=True)`
  - `correo = models.EmailField(blank=True, null=True)`
  - `activo = models.BooleanField(default=True)`
  - `fecha_registro = models.DateField(auto_now_add=True)`
  - **def** `__str__(self)` (L26)
  - **class** `Meta` (L29)
    - `verbose_name = 'Promotor'`
- **class** `Inversionista(models.Model)` (L34)
  - `tipo_contribuyente = models.CharField(max_length=10, choices=TIPO_CONTRIBUYENTE, default='fisica')`
  - `es_entidad_financiera = models.BooleanField(default=False)`
  - `nombre_completo = models.CharField(max_length=300)`
  - `nacionalidad = models.CharField(max_length=100, default='Mexicana')`
  - `curp = models.CharField(max_length=18, blank=True, null=True, unique=True)`
  - `fecha_nacimiento = models.DateField(null=True, blank=True)`
  - `correo = models.EmailField(blank=True)`
  - `telefono = models.CharField(max_length=20, blank=True)`
  - `fecha_ingreso = models.DateField(auto_now_add=True)`
  - `tipo_documento = models.CharField(max_length=20, choices=TIPO_DOCUMENTO, default='ine')`
  - `numero_documento = models.CharField(max_length=50, blank=True)`
  - `estado_civil = models.CharField(max_length=15, choices=ESTADO_CIVIL, default='soltero')`
  - `calle = models.CharField(max_length=300, blank=True)`
  - `ciudad = models.CharField(max_length=100, blank=True)`
  - `estado = models.CharField(max_length=100, blank=True)`
  - `codigo_postal = models.CharField(max_length=10, blank=True)`
  - `rfc = models.CharField(max_length=13, blank=True, null=True, unique=True)`
  - `regimen_fiscal = models.CharField(max_length=200, default='Régimen de Intereses')`
  - `nombre_fiscal = models.CharField(max_length=300, blank=True)`
  - `pais_fiscal = models.CharField(max_length=100, default='México')`
  - `estado_fiscal = models.CharField(max_length=100, blank=True)`
  - `cp_fiscal = models.CharField(max_length=10, blank=True)`
  - `banco = models.CharField(max_length=20, choices=BANCO_CHOICES, blank=True)`
  - `clabe = models.CharField(max_length=18, blank=True)`
  - `eliminado = models.BooleanField(default=False)`
  - `fecha_eliminado = models.DateTimeField(null=True, blank=True)`
  - `promotor = models.ForeignKey(Promotor, null=True, blank=True, on_delete=models.SET_NULL, related_name='inver...`
  - `periodicidad_pago = models.IntegerField(choices=PERIODICIDAD_CHOICES, default=28)`
  - `dias_cierre_fijo = models.PositiveIntegerField(null=True, blank=True, help_text='Si se define, el cierre SIEMPRE usa...`
  - **def** `__str__(self)` (L113)
  - **class** `Meta` (L116)
    - `verbose_name = 'Inversionista'`
- **class** `Inversion(models.Model)` (L121)
  - `inversionista = models.ForeignKey(Inversionista, on_delete=models.CASCADE, related_name='inversiones')`
  - `capital = models.DecimalField(max_digits=14, decimal_places=2)`
  - `tasa_anual = models.DecimalField(max_digits=5, decimal_places=2, help_text='Porcentaje, ej. 15.00')`
  - `base_calculo = models.IntegerField(choices=BASE_CHOICES, default=365)`
  - `porcentaje_factura = models.DecimalField(max_digits=10, decimal_places=5, default=100, help_text='% que se factura, el...`
  - `fecha_inicio = models.DateField()`
  - `fecha_vencimiento = models.DateField(null=True, blank=True)`
  - `estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='activo')`
  - `notas = models.TextField(blank=True)`
  - `renovacion_de = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='renovac...`
  - `numero_renovacion = models.PositiveIntegerField(default=0)`
  - `@property` **def** `porcentaje_externo(self)` (L154)
  - **def** `__str__(self)` (L157)
  - **class** `Meta` (L160)
    - `verbose_name = 'Inversión'`
- **class** `EstadoDeCuenta(models.Model)` (L165)
  - `inversionista = models.ForeignKey(Inversionista, on_delete=models.CASCADE, related_name='estados_de_cuenta', null...`
  - `inversion = models.ForeignKey(Inversion, on_delete=models.CASCADE, related_name='estados_de_cuenta', null=Tru...`
  - `periodo_inicio = models.DateField()`
  - `periodo_fin = models.DateField()`
  - `dias_periodo = models.IntegerField()`
  - `interes_bruto = models.DecimalField(max_digits=14, decimal_places=2)`
  - `isr = models.DecimalField(max_digits=14, decimal_places=2)`
  - `iva = models.DecimalField(max_digits=14, decimal_places=2)`
  - `interes_neto = models.DecimalField(max_digits=14, decimal_places=2)`
  - `pago_externo = models.DecimalField(max_digits=14, decimal_places=2, default=0)`
  - `total_pagar = models.DecimalField(max_digits=14, decimal_places=2)`
  - `estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='pendiente')`
  - `fecha_generado = models.DateTimeField(auto_now_add=True)`
  - `notas = models.TextField(blank=True)`
  - **def** `__str__(self)` (L198)
  - **class** `Meta` (L202)
    - `verbose_name = 'Estado de Cuenta'`
    - `unique_together = [['inversionista', 'periodo_inicio']]`
- **class** `Pago(models.Model)` (L209)
  - `estado_de_cuenta = models.OneToOneField(EstadoDeCuenta, on_delete=models.CASCADE, related_name='pago')`
  - `metodo = models.CharField(max_length=20, choices=METODO_CHOICES)`
  - `fecha_pago = models.DateField(null=True, blank=True)`
  - `estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='pendiente')`
  - `folio = models.CharField(max_length=30, blank=True)`
  - `notas = models.TextField(blank=True)`
  - `confirmado_por = models.CharField(max_length=200, blank=True)`
  - **def** `__str__(self)` (L232)
  - **class** `Meta` (L235)
    - `verbose_name = 'Pago'`
- **class** `Prospecto(models.Model)` (L240)
  - `nombre_completo = models.CharField(max_length=300)`
  - `telefono = models.CharField(max_length=20, blank=True)`
  - `correo = models.EmailField(blank=True)`
  - `monto_estimado = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)`
  - `promotor = models.ForeignKey(Promotor, null=True, blank=True, on_delete=models.SET_NULL, related_name='prosp...`
  - `etapa = models.CharField(max_length=15, choices=ETAPA_CHOICES, default='inicial')`
  - `notas = models.TextField(blank=True)`
  - `fecha_registro = models.DateField(auto_now_add=True)`
  - `convertido = models.BooleanField(default=False)`
  - `inversionista = models.OneToOneField(Inversionista, null=True, blank=True, on_delete=models.SET_NULL, related_nam...`
  - **def** `__str__(self)` (L266)
  - **class** `Meta` (L269)
    - `verbose_name = 'Prospecto'`
- **class** `Movimiento(models.Model)` (L273)
  - `inversion = models.ForeignKey(Inversion, on_delete=models.CASCADE, related_name='movimientos')`
  - `tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)`
  - `monto = models.DecimalField(max_digits=14, decimal_places=2)`
  - `fecha = models.DateField()`
  - `notas = models.TextField(blank=True)`
  - `fecha_registro = models.DateTimeField(auto_now_add=True)`
  - **def** `__str__(self)` (L289)
  - **class** `Meta` (L292)
    - `verbose_name = 'Movimiento'`
    - `ordering = ['fecha']`
- **class** `BugReport(models.Model)` (L297)
  - `tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)`
  - `pagina = models.CharField(max_length=200)`
  - `descripcion = RichTextField()`
  - `esperado = RichTextField(blank=True)`
  - `url_actual = models.URLField(blank=True)`
  - `usuario = models.CharField(max_length=200, blank=True)`
  - `fecha = models.DateTimeField(auto_now_add=True)`
  - `resuelto = models.BooleanField(default=False)`
  - **def** `__str__(self)` (L315)
  - **class** `Meta` (L318)
    - `verbose_name = 'Reporte de Error'`
    - `ordering = ['-fecha']`
- **class** `NotificacionDismissed(models.Model)` (L324) — Track dismissed notifications to prevent showing them again until next day
  - `inversion = models.ForeignKey(Inversion, on_delete=models.CASCADE, related_name='notificaciones_dismissed')`
  - `fecha_dismissed = models.DateField(auto_now_add=True)`
  - **class** `Meta` (L332)
    - `verbose_name = 'Notificación Descartada'`
    - `unique_together = [['inversion', 'fecha_dismissed']]`
  - **def** `__str__(self)` (L337)

### `inversiones/serializers.py`
- **class** `PromotorSerializer(serializers.ModelSerializer)` (L7)
  - `total_referidos = serializers.SerializerMethodField()`
  - `capital_total = serializers.SerializerMethodField()`
  - **class** `Meta` (L11)
    - `model = Promotor`
    - `fields = '__all__'`
  - **def** `get_total_referidos(self, obj)` (L15)
  - **def** `get_capital_total(self, obj)` (L18)
- **class** `MovimientoSerializer(serializers.ModelSerializer)` (L27)
  - `tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)`
  - **class** `Meta` (L30)
    - `model = Movimiento`
    - `fields = '__all__'`
- **class** `InversionSerializer(serializers.ModelSerializer)` (L35)
  - `porcentaje_externo = serializers.ReadOnlyField()`
  - `estado_display = serializers.CharField(source='get_estado_display', read_only=True)`
  - `base_display = serializers.CharField(source='get_base_calculo_display', read_only=True)`
  - `movimientos = MovimientoSerializer(many=True, read_only=True)`
  - `folio_display = serializers.SerializerMethodField()`
  - **class** `Meta` (L42)
    - `model = Inversion`
    - `fields = '__all__'`
  - **def** `get_folio_display(self, obj)` (L46)
- **class** `InversionistaSerializer(serializers.ModelSerializer)` (L51)
  - `promotor_nombre = serializers.CharField(source='promotor.nombre', read_only=True)`
  - `inversiones = InversionSerializer(many=True, read_only=True)`
  - `tipo_display = serializers.CharField(source='get_tipo_contribuyente_display', read_only=True)`
  - `estado_civil_display = serializers.CharField(source='get_estado_civil_display', read_only=True)`
  - `documento_display = serializers.CharField(source='get_tipo_documento_display', read_only=True)`
  - `banco_display = serializers.CharField(source='get_banco_display', read_only=True)`
  - **class** `Meta` (L59)
    - `model = Inversionista`
    - `fields = '__all__'`
- **class** `InversionistaListSerializer(serializers.ModelSerializer)` (L64) — Lightweight serializer for the list view (no nested inversiones).
  - `promotor_nombre = serializers.CharField(source='promotor.nombre', read_only=True)`
  - `tipo_display = serializers.CharField(source='get_tipo_contribuyente_display', read_only=True)`
  - `inversion_activa = serializers.SerializerMethodField()`
  - **class** `Meta` (L70)
    - `model = Inversionista`
    - `fields = ['id', 'nombre_completo', 'rfc', 'tipo_contribuyente', 'tipo_display', 'correo', 'telefono', 'pro...`
  - **def** `get_inversion_activa(self, obj)` (L79)
- **class** `EstadoDeCuentaSerializer(serializers.ModelSerializer)` (L92)
  - `inversionista_nombre = serializers.SerializerMethodField()`
  - `inversionista_rfc = serializers.SerializerMethodField()`
  - `estado_display = serializers.CharField(source='get_estado_display', read_only=True)`
  - **class** `Meta` (L97)
    - `model = EstadoDeCuenta`
    - `fields = '__all__'`
  - **def** `get_inversionista_nombre(self, obj)` (L101)
  - **def** `get_inversionista_rfc(self, obj)` (L108)
- **class** `PagoSerializer(serializers.ModelSerializer)` (L116)
  - `inversionista_nombre = serializers.SerializerMethodField()`
  - `inversionista_rfc = serializers.SerializerMethodField()`
  - `metodo_display = serializers.CharField(source='get_metodo_display', read_only=True)`
  - `estado_display = serializers.CharField(source='get_estado_display', read_only=True)`
  - `total_pagar = serializers.DecimalField(source='estado_de_cuenta.total_pagar', max_digits=14, decimal_places=2, ...`
  - `capital = serializers.SerializerMethodField()`
  - `interes_neto = serializers.DecimalField(source='estado_de_cuenta.interes_neto', max_digits=14, decimal_places=2,...`
  - `pago_externo = serializers.DecimalField(source='estado_de_cuenta.pago_externo', max_digits=14, decimal_places=2,...`
  - `estado_de_cuenta_detalle = serializers.SerializerMethodField()`
  - **class** `Meta` (L136)
    - `model = Pago`
    - `fields = '__all__'`
  - **def** `_get_inv(self, obj)` (L140)
  - **def** `get_inversionista_nombre(self, obj)` (L148)
  - **def** `get_inversionista_rfc(self, obj)` (L152)
  - **def** `get_capital(self, obj)` (L156)
  - **def** `get_estado_de_cuenta_detalle(self, obj)` (L165)
- **class** `ProspectoSerializer(serializers.ModelSerializer)` (L191)
  - `promotor_nombre = serializers.CharField(source='promotor.nombre', read_only=True)`
  - `etapa_display = serializers.CharField(source='get_etapa_display', read_only=True)`
  - **class** `Meta` (L195)
    - `model = Prospecto`
    - `fields = '__all__'`
- **class** `CalculadoraInputSerializer(serializers.Serializer)` (L201)
  - `capital = serializers.DecimalField(max_digits=14, decimal_places=2)`
  - `tasa_anual = serializers.DecimalField(max_digits=5, decimal_places=2)`
  - `dias = serializers.IntegerField(min_value=1, max_value=366)`
  - `base = serializers.ChoiceField(choices=[360, 365])`
  - `porcentaje_factura = serializers.DecimalField(max_digits=10, decimal_places=6, min_value=0, max_value=100)`

### `inversiones/tests.py`
_(no classes or functions)_

### `inversiones/urls.py`
- **URL patterns:**
  - `path('login/', views.login_view, name='login')` (L7)
  - `path('logout/', views.logout_view, name='logout')` (L8)
  - `path('register/', views.register_view, name='register')` (L9)
  - `path('', views.dashboard_view, name='dashboard')` (L12)
  - `path('inversionistas/', views.inversionistas_view, name='inversionistas')` (L13)
  - `path('calculadora/', views.calculadora_view, name='calculadora')` (L14)
  - `path('estados/', views.estados_view, name='estados')` (L15)
  - `path('pagos/', views.pagos_view, name='pagos')` (L16)
  - `path('promotores/', views.promotores_view, name='promotores')` (L17)
  - `path('prospectos/', views.prospectos_view, name='prospectos')` (L18)
  - `path('api/dashboard/', views.dashboard_summary, name='api-dashboard')` (L21)
  - `path('api/inversionistas/', views.inversionistas_list, name='api-inversionistas-list')` (L24)
  - `path('api/inversionistas/<int:pk>/', views.inversionista_detail, name='api-inversionista-detail')` (L25)
  - `path('api/inversiones/', views.inversiones_list, name='api-inversiones-list')` (L28)
  - `path('api/inversiones/<int:pk>/', views.inversion_detail, name='api-inversion-detail')` (L29)
  - `path('api/inversiones/<int:pk>/renovar/', views.renovar_inversion, name='api-renovar-inversion')` (L30)
  - `path('api/inversiones/<int:inversion_pk>/movimientos/', views.movimientos_list)` (L31)
  - `path('api/movimientos/<int:pk>/', views.movimiento_detail)` (L34)
  - `path('api/calculadora/', views.calcular_intereses, name='api-calculadora')` (L37)
  - `path('api/estados/', views.estados_list, name='api-estados-list')` (L40)
  - `path('api/estados/generar-todos/', views.generar_estados_todos, name='api-generar-todos')` (L41)
  - `path('api/estados/generar-inversionista/', views.generar_estado_inversionista, name='api-generar-estado-inversionista')` (L42)
  - `path('api/estados/enviar-todos/', views.enviar_estados_todos, name='api-enviar-todos')` (L43)
  - `path('api/estados/<int:pk>/', views.estado_detail, name='api-estado-detail')` (L44)
  - `path('api/estados/<int:pk>/preview/', views.estado_preview, name='api-estado-preview')` (L45)
  - `path('api/estados/<int:pk>/pdf-preview/', views.estado_pdf_preview, name='api-estado-pdf-preview')` (L46)
  - `path('api/estados/<int:pk>/enviar/', views.estado_enviar, name='api-estado-enviar')` (L47)
  - `path('api/estados/<int:pk>/pdf-datos/', views.estado_pdf_datos, name='api-estado-pdf-datos')` (L48)
  - `path('api/pagos/', views.pagos_list, name='api-pagos-list')` (L51)
  - `path('api/pagos/<int:pk>/', views.pago_detail, name='api-pago-detail')` (L52)
  - `path('api/pagos/<int:pk>/marcar-pagado/', views.marcar_pagado, name='api-marcar-pagado')` (L53)
  - `path('api/promotores/', views.promotores_list, name='api-promotores-list')` (L56)
  - `path('api/promotores/<int:pk>/', views.promotor_detail, name='api-promotor-detail')` (L57)
  - `path('api/prospectos/', views.prospectos_list, name='api-prospectos-list')` (L60)
  - `path('api/prospectos/<int:pk>/', views.prospecto_detail, name='api-prospecto-detail')` (L61)
  - `path('api/prospectos/<int:pk>/convertir/', views.convertir_prospecto, name='api-convertir-prospecto')` (L62)
  - `path('api/bug-report/', views.bug_report, name='api-bug-report')` (L65)
  - `path('papelera/', views.papelera_view, name='papelera')` (L68)
  - `path('api/papelera/', views.papelera_list)` (L69)
  - `path('api/papelera/<int:pk>/restaurar/', views.restaurar_inversionista)` (L70)
  - `path('api/inversionistas/<int:pk>/eliminar-permanente/', views.eliminar_permanente)` (L71)
  - `path('api/estados/exportar-excel/', views.exportar_excel_estados)` (L74)
  - `path('api/notificaciones/dismiss/', views.dismiss_notification, name='api-dismiss-notification')` (L75)

### `inversiones/views.py`
- **def** `honeypot_view(request)` (L46)
- **def** `login_view(request)` (L87)
- **def** `logout_view(request)` (L106)
- **def** `register_view(request)` (L110)
- `@login_required(login_url='login')` **def** `dashboard_view(request)` (L160)
- `@login_required(login_url='login')` **def** `inversionistas_view(request)` (L164)
- `@login_required(login_url='login')` **def** `calculadora_view(request)` (L168)
- `@login_required(login_url='login')` **def** `estados_view(request)` (L172)
- `@login_required(login_url='login')` **def** `pagos_view(request)` (L176)
- `@login_required(login_url='login')` **def** `promotores_view(request)` (L180)
- `@login_required(login_url='login')` **def** `prospectos_view(request)` (L184)
- `@login_required(login_url='login')` **def** `papelera_view(request)` (L188)
- `@api_view(['GET', 'POST'])` **def** `inversionistas_list(request)` (L196) — GET /api/inversionistas/ — list all investors
- `@api_view(['GET', 'PUT', 'DELETE'])` **def** `inversionista_detail(request, pk)` (L233) — GET /api/inversionistas/<pk>/ — get single investor with all inversiones
- `@api_view(['GET'])` **def** `papelera_list(request)` (L261) — GET /api/papelera/ — list soft-deleted investors
- `@api_view(['POST'])` **def** `restaurar_inversionista(request, pk)` (L269) — POST /api/papelera/<pk>/restaurar/ — restore a soft-deleted investor
- `@api_view(['GET', 'POST'])` **def** `inversiones_list(request)` (L282) — GET /api/inversiones/ — list all inversiones (filter by ?estado=activo etc.)
- `@api_view(['GET', 'PUT', 'DELETE'])` **def** `inversion_detail(request, pk)` (L304)
- `@api_view(['POST'])` **def** `renovar_inversion(request, pk)` (L323) — POST /api/inversiones/<pk>/renovar/
- `@api_view(['GET', 'POST'])` **def** `movimientos_list(request, inversion_pk)` (L378) — GET /api/inversiones/<pk>/movimientos/ — list movements for an investment
- `@api_view(['DELETE'])` **def** `movimiento_detail(request, pk)` (L408) — DELETE /api/movimientos/<pk>/ — remove a movement and reverse its effect on capital
- `@api_view(['POST'])` **def** `calcular_intereses(request)` (L428) — POST /api/calculadora/
- `@api_view(['GET', 'POST'])` **def** `estados_list(request)` (L479) — GET /api/estados/ — list all estados (filter by ?estado=pendiente)
- `@api_view(['GET', 'PUT', 'DELETE'])` **def** `estado_detail(request, pk)` (L514)
- `@api_view(['POST'])` `@login_required(login_url='login')` **def** `generar_estados_todos(request)` (L535) — POST /api/estados/generar-todos/
- `@api_view(['POST'])` `@login_required(login_url='login')` **def** `generar_estado_inversionista(request)` (L669) — POST /api/estados/generar-inversionista/
- **def** `_totales_facturados(inversiones, periodo_inicio, periodo_fin)` (L761) — Suma SOLO la parte facturada de cada inversión.
- **def** `_calcular_interes_con_movimientos(inversion, periodo_inicio, periodo_fin)` (L779) — Calculates interest for a period using pro-rated tranches.
- `@api_view(['GET'])` **def** `pagos_list(request)` (L876) — GET /api/pagos/ — list all pagos (filter by ?estado=pendiente&mes=2026-03)
- `@api_view(['GET', 'PUT', 'DELETE'])` **def** `pago_detail(request, pk)` (L896)
- `@api_view(['POST'])` **def** `marcar_pagado(request, pk)` (L916) — POST /api/pagos/<pk>/marcar-pagado/
- `@api_view(['GET', 'POST'])` **def** `promotores_list(request)` (L951)
- `@api_view(['GET', 'PUT', 'DELETE'])` **def** `promotor_detail(request, pk)` (L982)
- `@api_view(['GET', 'POST'])` **def** `prospectos_list(request)` (L1006)
- `@api_view(['GET', 'PUT', 'DELETE'])` **def** `prospecto_detail(request, pk)` (L1024)
- `@api_view(['POST'])` **def** `convertir_prospecto(request, pk)` (L1044) — POST /api/prospectos/<pk>/convertir/
- `@api_view(['GET'])` **def** `dashboard_summary(request)` (L1080) — GET /api/dashboard/
- `@api_view(['GET'])` `@login_required(login_url='login')` **def** `estado_preview(request, pk)` (L1241)
- **def** `_build_estado_pdf(data)` (L1279) — Builds a PDF Estado de Cuenta that mirrors the Ideaconv PDF format.
- **def** `_build_email_html(data, notas_extra='', tipo_comprobante='ambos')` (L1761) — Clean notification-style HTML email.
- **def** `_build_estado_data(estado, inv_obj, overrides=None)` (L1888) — Builds the full `data` dict (incl. per-investment tranche rows) for a single
- **def** `_aplicar_overrides(data, overrides)` (L2056) — Overwrites computed PDF values with numbers the user typed in the send modal.
- **def** `_resolver_inversionista(estado)` (L2128) — Works for both old (inversion FK) and new (inversionista FK) records.
- `@api_view(['GET'])` `@login_required(login_url='login')` **def** `estado_pdf_datos(request, pk)` (L2141) — GET /api/estados/<pk>/pdf-datos/
- `@api_view(['GET', 'POST'])` `@login_required(login_url='login')` `@xframe_options_sameorigin` **def** `estado_pdf_preview(request, pk)` (L2176) — GET /api/estados/<pk>/pdf-preview/?nota_pdf=<msg>
- `@api_view(['POST'])` `@login_required(login_url='login')` **def** `estado_enviar(request, pk)` (L2211) — POST /api/estados/<pk>/enviar/
- `@api_view(['POST'])` `@login_required(login_url='login')` **def** `enviar_estados_todos(request)` (L2281) — POST /api/estados/enviar-todos/
- `@api_view(['POST'])` `@login_required(login_url='login')` **def** `bug_report(request)` (L2360)
- `@api_view(['POST'])` `@login_required(login_url='login')` **def** `dismiss_notification(request)` (L2374) — POST /api/notificaciones/dismiss/
- `@api_view(['GET', 'DELETE'])` **def** `eliminar_permanente(request, pk)` (L2405)
- `@api_view(['GET'])` `@login_required(login_url='login')` **def** `exportar_excel_estados(request)` (L2455) — GET /api/estados/exportar-excel/?periodo_inicio=2026-04-01&periodo_fin=2026-04-30

### `manage.py`
- **def** `main()` (L7) — Run administrative tasks.

### `migrate_investors_standalone.py`
- **def** `normalize_name(name)` (L29) — Normalize name for matching
- **def** `get_or_create_promotor(nombre)` (L35) — Get or create a Promotor by name

### `transform_only.py`
_(no classes or functions)_

## JavaScript

_none found_

## Skipped / problems

- `reconstruir_estados.py`: could not parse: '(' was never closed (<unknown>, line 185)
