import hashlib
import secrets
import uuid

from django.db import models

from core.crypto import cifrar_campo, descifrar_campo


class SistemaIntegrado(models.Model):
    """Sistema legado externo autorizado a conectarse vía la API pública
    (/api/v1/, ver SKL-DEV-003 y la regla R-ARN-004 del arnés: cualquier
    cambio de firma de estos endpoints es un cambio estructural).

    Patrón de API key (igual a GitHub PATs / tokens de Stripe): se genera un
    token aleatorio de 256 bits que se muestra al usuario UNA sola vez; solo
    se persiste su hash SHA-256. A diferencia de una contraseña elegida por
    una persona, este token ya tiene alta entropía, por lo que un hash simple
    (no bcrypt/Argon2, pensados para contrarrestar el poco espacio de
    búsqueda de contraseñas humanas) es suficiente y evita cómputo innecesario
    en cada request autenticado.
    """

    class Estado(models.TextChoices):
        ACTIVO = "ACTIVO", "Activo"
        REVOCADO = "REVOCADO", "Revocado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=150)
    api_key_hash = models.CharField(
        max_length=64,
        unique=True,
        editable=False,
        help_text="SHA-256 de la API key. La key en texto plano nunca se persiste; ver crear_con_api_key().",
    )
    scopes = models.JSONField(
        default=list, blank=True, help_text="Lista de endpoints/acciones permitidas a este sistema."
    )
    contacto_tecnico = models.CharField(max_length=255, blank=True)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.ACTIVO)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Sistema integrado"
        verbose_name_plural = "Sistemas integrados"

    def __str__(self):
        return self.nombre

    @staticmethod
    def _hash_api_key(api_key: str) -> str:
        return hashlib.sha256(api_key.encode("utf-8")).hexdigest()

    @classmethod
    def crear_con_api_key(cls, **kwargs) -> tuple["SistemaIntegrado", str]:
        """Crea el registro y genera su API key. Devuelve (instancia, api_key_en_claro).

        La key en claro solo existe en este valor de retorno — mostrarla al
        usuario de inmediato; no queda almacenada en ningún lugar del sistema.
        """
        api_key = secrets.token_urlsafe(32)
        instancia = cls.objects.create(api_key_hash=cls._hash_api_key(api_key), **kwargs)
        return instancia, api_key

    @classmethod
    def verificar_api_key(cls, api_key: str) -> "SistemaIntegrado | None":
        """Usado por la autenticación de la API (/api/v1/) para resolver el llamador."""
        return cls.objects.filter(
            api_key_hash=cls._hash_api_key(api_key), estado=cls.Estado.ACTIVO
        ).first()


class ContratoEncargado(models.Model):
    """Mandato de tratamiento de datos (Art. 15 bis) con un sistema integrado.

    Se activa porque, al recibir datos personales de un sistema externo para
    procesarlos, esta plataforma actúa como encargado de tratamiento de ese
    sistema (ver decisión de arquitectura registrada en memoria de proyecto).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sistema_integrado = models.ForeignKey(
        SistemaIntegrado, on_delete=models.CASCADE, related_name="contratos_encargado"
    )
    documento = models.FileField(upload_to="contratos_encargado/%Y/%m/")
    fecha_firma = models.DateField()
    vigente = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Contrato de encargado"
        verbose_name_plural = "Contratos de encargado"

    def __str__(self):
        return f"Contrato — {self.sistema_integrado.nombre}"


class WebhookSuscripcion(models.Model):
    """Suscripción de un sistema integrado a eventos salientes de la plataforma.

    A diferencia de la API key (arriba), el secreto HMAC sí debe poder
    recuperarse en claro para firmar cada payload saliente, así que no puede
    guardarse como hash — se guarda cifrado con AES-256-GCM (core.crypto),
    igual que el RUT del titular.
    """

    class Evento(models.TextChoices):
        PURGA_EJECUTADA = "PURGA_EJECUTADA", "Purga/anonimización ejecutada"
        ARCO_RESUELTA = "ARCO_RESUELTA", "Solicitud ARCO resuelta"
        CONSENTIMIENTO_REVOCADO = "CONSENTIMIENTO_REVOCADO", "Consentimiento revocado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sistema_integrado = models.ForeignKey(
        SistemaIntegrado, on_delete=models.CASCADE, related_name="webhooks"
    )
    url_destino = models.URLField()
    eventos_suscritos = models.JSONField(
        default=list, help_text=f"Subconjunto de: {[e.value for e in Evento]}"
    )
    secreto_cifrado = models.TextField(
        editable=False, help_text="Secreto HMAC cifrado (AES-256-GCM). Usar generar_secreto()/secreto."
    )
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Suscripción a webhook"
        verbose_name_plural = "Suscripciones a webhook"

    def __str__(self):
        return f"{self.sistema_integrado.nombre} → {self.url_destino}"

    @property
    def secreto(self) -> str:
        return descifrar_campo(self.secreto_cifrado)

    def generar_secreto(self) -> str:
        """Genera y almacena (cifrado) un nuevo secreto HMAC. Devuelve el valor en claro para mostrarlo una vez."""
        valor = secrets.token_urlsafe(32)
        self.secreto_cifrado = cifrar_campo(valor)
        return valor


class WebhookEntrega(models.Model):
    """Log de intentos de entrega de un webhook, para depuración y reintentos."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    suscripcion = models.ForeignKey(
        WebhookSuscripcion, on_delete=models.CASCADE, related_name="entregas"
    )
    evento = models.CharField(max_length=50)
    payload = models.JSONField()
    status_code = models.PositiveIntegerField(null=True, blank=True)
    intentos = models.PositiveIntegerField(default=0)
    entregado = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Entrega de webhook"
        verbose_name_plural = "Entregas de webhook"
        ordering = ["-timestamp"]

    def __str__(self):
        estado = "OK" if self.entregado else "pendiente"
        return f"{self.evento} → {self.suscripcion_id} ({estado})"
