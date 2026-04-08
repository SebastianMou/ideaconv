from django.urls import path
from . import views


urlpatterns = [
    path('login/',  views.login_view,  name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),

    # Template / Page URLs
    path('', views.dashboard_view, name='dashboard'),
    path('inversionistas/', views.inversionistas_view, name='inversionistas'),
    path('calculadora/', views.calculadora_view, name='calculadora'),
    path('estados/', views.estados_view, name='estados'),
    path('pagos/', views.pagos_view, name='pagos'),
    path('promotores/', views.promotores_view, name='promotores'),
    path('prospectos/', views.prospectos_view, name='prospectos'),

    # Dashboard API
    path('api/dashboard/', views.dashboard_summary, name='api-dashboard'),

    # Inversionistas API
    path('api/inversionistas/', views.inversionistas_list, name='api-inversionistas-list'),
    path('api/inversionistas/<int:pk>/', views.inversionista_detail, name='api-inversionista-detail'),

    # Inversiones API
    path('api/inversiones/', views.inversiones_list, name='api-inversiones-list'),
    path('api/inversiones/<int:pk>/', views.inversion_detail, name='api-inversion-detail'),

    # Calculadora API
    path('api/calculadora/', views.calcular_intereses, name='api-calculadora'),

    # Estados de Cuenta API
    path('api/estados/', views.estados_list, name='api-estados-list'),
    path('api/estados/<int:pk>/', views.estado_detail, name='api-estado-detail'),
    path('api/estados/generar-todos/', views.generar_estados_todos, name='api-generar-todos'),

    # Pagos API
    path('api/pagos/', views.pagos_list, name='api-pagos-list'),
    path('api/pagos/<int:pk>/', views.pago_detail, name='api-pago-detail'),
    path('api/pagos/<int:pk>/marcar-pagado/', views.marcar_pagado, name='api-marcar-pagado'),

    # Promotores API
    path('api/promotores/', views.promotores_list, name='api-promotores-list'),
    path('api/promotores/<int:pk>/', views.promotor_detail, name='api-promotor-detail'),

    # Prospectos API
    path('api/prospectos/', views.prospectos_list, name='api-prospectos-list'),
    path('api/prospectos/<int:pk>/', views.prospecto_detail, name='api-prospecto-detail'),
    path('api/prospectos/<int:pk>/convertir/', views.convertir_prospecto, name='api-convertir-prospecto'),

    path('api/estados/<int:pk>/preview/', views.estado_preview, name='api-estado-preview'),
    path('api/estados/<int:pk>/enviar/', views.estado_enviar, name='api-estado-enviar'),
    path('api/estados/enviar-todos/', views.enviar_estados_todos, name='api-enviar-todos'),

    path('api/bug-report/', views.bug_report, name='api-bug-report'),

]
