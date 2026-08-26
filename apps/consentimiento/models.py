import hashlib
import uuid

from django.db import models


class PoliticaPrivacidad(models.Model):
    """Versión publicada de la política de privacidad (CTX-003 §1.A).

    El hash permite demostrar, ante una auditoría, que el texto que un titular
    aceptó no fue alterado retroactivamente.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version = models.CharField(max_length=20, unique=True)
    texto = models.TextField()
    hash_sha256 = models.CharField(max_length=64, editable=False)
    vigente = models.BooleanField(default=True)
    fecha_publicacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Política de privacidad"
        verbose_name_plural = "Políticas de privacidad"

    def __str__(self):
        return self.version

    def save(self, *args, **kwargs):
        self.hash_sha256 = hashlib.sha256(self.texto.encode()).hexdigest()
        super().save(*args, **kwargs)


class RegistroConsentimiento(models.Model):
    """Log de aceptación/revocación de consentimiento (CTX-003 §1.A, Art. 12).

    No se permiten autorizaciones genéricas: cada registro queda atado a una
    ActividadTratamiento (finalidad) específica.
    """

    class Estado(models.TextChoices):
        OTORGADO = "OTORGADO", "Otorgado"
        REVOCADO = "REVOCADO", "Revocado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    titular = models.ForeignKey(
        "titulares.Titular", on_delete=models.CASCADE, related_name="consentimientos"
    )
    politica = models.ForeignKey(
        PoliticaPrivacidad, on_delete=models.PROTECT, related_name="registros"
    )
    actividad = models.ForeignKey(
        "rat.ActividadTratamiento", on_delete=models.PROTECT, related_name="consentimientos"
    )
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.OTORGADO)
    canal_origen = models.CharField(max_length=255, blank=True, help_text="URL o canal donde se otorgó.")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    integracion_origen = models.ForeignKey(
        "integraciones.SistemaIntegrado",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="consentimientos_registrados",
    )
    fecha_otorgamiento = models.DateTimeField(auto_now_add=True)
    fecha_revocacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Registro de consentimiento"
        verbose_name_plural = "Registros de consentimiento"
        indexes = [models.Index(fields=["titular", "actividad"])]

    def __str__(self):
        return f"{self.titular_id} — {self.actividad_id} — {self.estado}"
