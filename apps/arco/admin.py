from django.contrib import admin

from .models import SolicitudArco


@admin.register(SolicitudArco)
class SolicitudArcoAdmin(admin.ModelAdmin):
    list_display = ("titular", "tipo_derecho", "estado", "fecha_solicitud", "fecha_limite")
    list_filter = ("tipo_derecho", "estado")
    readonly_fields = ("fecha_solicitud", "fecha_limite")
