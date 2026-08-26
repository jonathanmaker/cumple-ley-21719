from django.contrib import admin

from .models import ContratoEncargado, SistemaIntegrado, WebhookEntrega, WebhookSuscripcion


@admin.register(SistemaIntegrado)
class SistemaIntegradoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "estado", "contacto_tecnico", "fecha_creacion")
    list_filter = ("estado",)
    readonly_fields = ("api_key_hash",)


@admin.register(ContratoEncargado)
class ContratoEncargadoAdmin(admin.ModelAdmin):
    list_display = ("sistema_integrado", "fecha_firma", "vigente")
    list_filter = ("vigente",)


@admin.register(WebhookSuscripcion)
class WebhookSuscripcionAdmin(admin.ModelAdmin):
    list_display = ("sistema_integrado", "url_destino", "activo")
    list_filter = ("activo",)
    readonly_fields = ("secreto_cifrado",)


@admin.register(WebhookEntrega)
class WebhookEntregaAdmin(admin.ModelAdmin):
    list_display = ("suscripcion", "evento", "status_code", "intentos", "entregado", "timestamp")
    list_filter = ("evento", "entregado")
