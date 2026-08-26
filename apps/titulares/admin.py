from django.contrib import admin

from .models import Titular


@admin.register(Titular)
class TitularAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo_titular", "email", "fecha_registro")
    list_filter = ("tipo_titular",)
    search_fields = ("nombre", "email", "rut_hash")
    readonly_fields = ("rut_hash", "rut_cifrado", "fecha_registro")
