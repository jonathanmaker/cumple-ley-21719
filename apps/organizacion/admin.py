from django.contrib import admin

from .models import Organizacion


@admin.register(Organizacion)
class OrganizacionAdmin(admin.ModelAdmin):
    list_display = ("razon_social", "rut", "rubro")
