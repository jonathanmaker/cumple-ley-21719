import uuid

from django.conf import settings
from django.db import models


class PerfilUsuario(models.Model):
    """Datos adicionales del usuario interno.

    Los roles y permisos usan los Groups/Permissions nativos de Django
    (auth.Group: ADMIN, DPD, RRHH, VENTAS, SOPORTE, LECTURA_RESTRINGIDA) en vez
    de una tabla de roles propia, para no reimplementar lo que Django ya da.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil"
    )
    departamento = models.CharField(max_length=100, blank=True)
    telefono = models.CharField(max_length=30, blank=True)

    class Meta:
        verbose_name = "Perfil de usuario"
        verbose_name_plural = "Perfiles de usuario"

    def __str__(self):
        return self.usuario.get_username()
