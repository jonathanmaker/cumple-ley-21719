from django.contrib import admin

from .models import PoliticaPrivacidad, RegistroConsentimiento


@admin.register(PoliticaPrivacidad)
class PoliticaPrivacidadAdmin(admin.ModelAdmin):
    list_display = ("version", "vigente", "fecha_publicacion")
    readonly_fields = ("hash_sha256",)


@admin.register(RegistroConsentimiento)
class RegistroConsentimientoAdmin(admin.ModelAdmin):
    list_display = ("titular", "actividad", "estado", "fecha_otorgamiento")
    list_filter = ("estado",)
    readonly_fields = ("fecha_otorgamiento",)
