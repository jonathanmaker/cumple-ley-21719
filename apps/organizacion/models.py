import uuid

from django.db import models


class Organizacion(models.Model):
    """Entidad legal responsable del tratamiento (Art. 2 letra ll).

    Modelo singleton por diseño: se espera un único registro por instancia
    (despliegue single-tenant, ver INDICE_MAESTRO.md del framework agéntico).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    razon_social = models.CharField(max_length=255)
    rut = models.CharField(max_length=20, unique=True)
    rubro = models.CharField(max_length=100, blank=True)
    direccion = models.CharField(max_length=255, blank=True)
    dpd_nombre = models.CharField(
        "Nombre del Delegado de Protección de Datos", max_length=255, blank=True
    )
    dpd_contacto = models.CharField(
        "Contacto del DPD (email o teléfono)", max_length=255, blank=True
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Organización"
        verbose_name_plural = "Organización"

    def __str__(self):
        return self.razon_social
