import hashlib
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class AuditLog(models.Model):
    """Bitácora de auditoría inmutable (CTX-004 §1.C, SKL-DEV-002 §3).

    Solo INSERT a nivel de aplicación (ver save()/delete() abajo) Y a nivel de
    base de datos: los permisos UPDATE/DELETE sobre esta tabla deben revocarse
    para el rol de aplicación en producción — eso se configura en el
    despliegue (Postgres), no aquí.

    La purga/anonimización no tiene tabla propia: se registra aquí con
    accion=PURGA o ANONIMIZACION, evitando duplicar lo que en esencia ya es
    un log.
    """

    class Accion(models.TextChoices):
        ACCESO = "ACCESO", "Acceso"
        MODIFICACION = "MODIFICACION", "Modificación"
        EXPORTACION = "EXPORTACION", "Exportación"
        PURGA = "PURGA", "Purga / eliminación"
        ANONIMIZACION = "ANONIMIZACION", "Anonimización"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(default=timezone.now, editable=False)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acciones_auditadas",
        help_text="Nulo si la acción provino de una integración externa (ver integracion_origen).",
    )
    integracion_origen = models.ForeignKey(
        "integraciones.SistemaIntegrado",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acciones_auditadas",
    )
    modulo = models.CharField(max_length=50)
    accion = models.CharField(max_length=20, choices=Accion.choices)
    descripcion = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    hash_registro = models.CharField(max_length=64, editable=False)

    class Meta:
        verbose_name = "Registro de auditoría"
        verbose_name_plural = "Registros de auditoría"
        ordering = ["-timestamp"]

    def save(self, *args, **kwargs):
        if self.pk and AuditLog.objects.filter(pk=self.pk).exists():
            raise ValueError("AuditLog es de solo inserción: no se permite modificar un registro existente.")
        payload = f"{self.timestamp.isoformat()}|{self.usuario_id}|{self.modulo}|{self.accion}|{self.descripcion}"
        self.hash_registro = hashlib.sha256(payload.encode()).hexdigest()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("AuditLog es de solo inserción: no se permite eliminar un registro existente.")

    def __str__(self):
        return f"[{self.timestamp}] {self.modulo}:{self.accion}"
