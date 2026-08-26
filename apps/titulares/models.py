import hashlib
import uuid

from django.db import models

from core.crypto import cifrar_campo, descifrar_campo


class Titular(models.Model):
    """Persona natural dueña de los datos personales tratados (Art. 2 letra f).

    Registro delgado a propósito: no busca ser la ficha completa del titular
    (eso lo mantiene el sistema legado cuando la organización usa la API de
    integración, ver apps.integraciones), solo lo necesario para trazar
    consentimiento, solicitudes ARCO y auditoría.
    """

    class TipoTitular(models.TextChoices):
        EMPLEADO = "EMPLEADO", "Empleado"
        CLIENTE = "CLIENTE", "Cliente"
        CANDIDATO = "CANDIDATO", "Candidato"
        PROVEEDOR = "PROVEEDOR", "Proveedor"
        MENOR_EDAD = "MENOR_EDAD", "Menor de edad (NNA)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rut_hash = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        editable=False,
        help_text="SHA-256 del RUT normalizado, para ubicar al titular sin desencriptar.",
    )
    rut_cifrado = models.TextField(
        blank=True,
        editable=False,
        help_text="RUT cifrado con AES-256-GCM (core.crypto). Usar la propiedad `rut`, no este campo directamente.",
    )
    nombre = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    tipo_titular = models.CharField(max_length=20, choices=TipoTitular.choices)
    integracion_origen = models.ForeignKey(
        "integraciones.SistemaIntegrado",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="titulares_creados",
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Titular de datos"
        verbose_name_plural = "Titulares de datos"

    def __str__(self):
        return self.nombre or str(self.id)

    @staticmethod
    def hash_rut(rut: str) -> str:
        return hashlib.sha256(rut.strip().upper().encode()).hexdigest()

    @property
    def rut(self) -> str:
        """Descifra el RUT bajo demanda. No se guarda en texto plano en ningún campo."""
        return descifrar_campo(self.rut_cifrado)

    @rut.setter
    def rut(self, valor: str) -> None:
        self.rut_hash = self.hash_rut(valor)
        self.rut_cifrado = cifrar_campo(valor)
