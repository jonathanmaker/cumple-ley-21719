import datetime
import uuid

from django.db import models
from django.utils import timezone


class SolicitudArco(models.Model):
    """Solicitud de derechos ARCO + Portabilidad + Bloqueo (CTX-003 §3, Art. 5-9 y 11)."""

    class TipoDerecho(models.TextChoices):
        ACCESO = "ACCESO", "Acceso"
        RECTIFICACION = "RECTIFICACION", "Rectificación"
        SUPRESION = "SUPRESION", "Supresión"
        OPOSICION = "OPOSICION", "Oposición"
        PORTABILIDAD = "PORTABILIDAD", "Portabilidad"
        BLOQUEO = "BLOQUEO", "Bloqueo temporal"

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        EN_PROCESO = "EN_PROCESO", "En proceso"
        RESUELTA = "RESUELTA", "Resuelta"
        RECHAZADA = "RECHAZADA", "Rechazada"

    PLAZO_RESPUESTA_DIAS = 30

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    titular = models.ForeignKey(
        "titulares.Titular", on_delete=models.CASCADE, related_name="solicitudes_arco"
    )
    tipo_derecho = models.CharField(max_length=20, choices=TipoDerecho.choices)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    canal_ingreso = models.CharField(max_length=100, blank=True)
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_limite = models.DateTimeField(
        editable=False, help_text="Calculada automáticamente: fecha_solicitud + 30 días corridos (Art. 11)."
    )
    fecha_prorroga = models.DateTimeField(
        null=True, blank=True, help_text="Solo si se notificó prórroga antes del vencimiento original."
    )
    fecha_resolucion = models.DateTimeField(null=True, blank=True)
    justificacion_rechazo = models.TextField(blank=True)
    archivo_respaldo = models.FileField(upload_to="arco_respaldos/%Y/%m/", null=True, blank=True)

    class Meta:
        verbose_name = "Solicitud ARCO"
        verbose_name_plural = "Solicitudes ARCO"
        ordering = ["-fecha_solicitud"]

    def save(self, *args, **kwargs):
        if not self.fecha_limite:
            base = self.fecha_solicitud or timezone.now()
            self.fecha_limite = base + datetime.timedelta(days=self.PLAZO_RESPUESTA_DIAS)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_tipo_derecho_display()} — {self.titular_id} — {self.estado}"
