from django.contrib import admin

from .models import ActividadTratamiento, Destinatario, MedidaSeguridad, PlantillaProceso, TipoDato


@admin.register(PlantillaProceso)
class PlantillaProcesoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "base_licitud_sugerida", "plazo_sugerido_meses")


@admin.register(TipoDato)
class TipoDatoAdmin(admin.ModelAdmin):
    list_display = ("categoria", "es_sensible", "es_biometrico")
    list_filter = ("es_sensible", "es_biometrico")


@admin.register(Destinatario)
class DestinatarioAdmin(admin.ModelAdmin):
    list_display = ("nombre_entidad", "tipo_destinatario", "pais_ubicacion", "es_encargado_tratamiento")
    list_filter = ("tipo_destinatario", "es_encargado_tratamiento")


@admin.register(MedidaSeguridad)
class MedidaSeguridadAdmin(admin.ModelAdmin):
    list_display = ("descripcion", "tipo_medida")


@admin.register(ActividadTratamiento)
class ActividadTratamientoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "base_licitud", "plazo_conservacion_meses", "activa")
    list_filter = ("base_licitud", "activa")
    filter_horizontal = ("tipos_dato", "destinatarios", "medidas_seguridad")
