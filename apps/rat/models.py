import uuid

from django.db import models


class BaseLicitud(models.TextChoices):
    """Bases de licitud del tratamiento (Art. 12 y 13)."""

    CONSENTIMIENTO = "CONSENTIMIENTO", "Consentimiento (Art. 12)"
    CONTRATO = "CONTRATO", "Ejecución contractual (Art. 13 letra c)"
    OBLIGACION_LEGAL = "OBLIGACION_LEGAL", "Obligación legal (Art. 13 letra b)"
    INTERES_LEGITIMO = "INTERES_LEGITIMO", "Interés legítimo (Art. 13 letra d)"
    DEFENSA_DERECHOS = "DEFENSA_DERECHOS", "Defensa de derechos (Art. 13 letra e)"
    DATOS_ECONOMICOS = "DATOS_ECONOMICOS", "Datos económicos/comerciales (Art. 13 letra a)"


class PlantillaProceso(models.Model):
    """Catálogo de procesos preconfigurados para el wizard de onboarding
    (CTX-002 §2.A: Selección de Personal, CRM, Facturación, Sueldos, CCTV,
    Control de Acceso Biométrico).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    base_licitud_sugerida = models.CharField(max_length=30, choices=BaseLicitud.choices)
    plazo_sugerido_meses = models.PositiveIntegerField(null=True, blank=True)
    campos_tipicos = models.JSONField(
        default=list, blank=True, help_text="Lista de nombres de TipoDato típicos de este proceso."
    )

    class Meta:
        verbose_name = "Plantilla de proceso"
        verbose_name_plural = "Plantillas de proceso"

    def __str__(self):
        return self.nombre


class TipoDato(models.Model):
    """Catálogo de categorías de datos personales tratados (CTX-002 §3: TIPO_DATO)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    categoria = models.CharField(max_length=100, unique=True)
    es_sensible = models.BooleanField(
        default=False, help_text="Datos sensibles conforme Art. 2 letra g (ver SKL-LEGAL-002)."
    )
    es_biometrico = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Tipo de dato"
        verbose_name_plural = "Tipos de dato"

    def __str__(self):
        return self.categoria


class Destinatario(models.Model):
    """Terceros a quienes se ceden o comparten datos (CTX-002 §3: DESTINATARIO)."""

    class TipoDestinatario(models.TextChoices):
        INTERNO = "INTERNO", "Interno"
        EXTERNO_NACIONAL = "EXTERNO_NACIONAL", "Externo nacional"
        EXTERNO_INTERNACIONAL = "EXTERNO_INTERNACIONAL", "Externo internacional"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre_entidad = models.CharField(max_length=255)
    tipo_destinatario = models.CharField(max_length=30, choices=TipoDestinatario.choices)
    pais_ubicacion = models.CharField(max_length=100, blank=True)
    es_encargado_tratamiento = models.BooleanField(
        default=False,
        help_text=(
            "Marca si procesa datos por cuenta de la organización (Art. 15 bis) "
            "y por tanto requiere un ContratoEncargado."
        ),
    )

    class Meta:
        verbose_name = "Destinatario"
        verbose_name_plural = "Destinatarios"

    def __str__(self):
        return self.nombre_entidad


class MedidaSeguridad(models.Model):
    """Catálogo de medidas de seguridad aplicables (CTX-002 §3: MEDIDA_SEGURIDAD)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    descripcion = models.CharField(max_length=255)
    tipo_medida = models.CharField(max_length=50)

    class Meta:
        verbose_name = "Medida de seguridad"
        verbose_name_plural = "Medidas de seguridad"

    def __str__(self):
        return self.descripcion


class ActividadTratamiento(models.Model):
    """Registro de Actividades de Tratamiento — RAT (CTX-002, principio de
    Responsabilidad Demostrable, Art. 3 letra g).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=150)
    finalidad = models.TextField()
    base_licitud = models.CharField(max_length=30, choices=BaseLicitud.choices)
    plazo_conservacion_meses = models.PositiveIntegerField(
        help_text="Vencido este plazo, el motor de retención anonimiza o elimina (módulo apps.auditoria)."
    )
    plantilla_origen = models.ForeignKey(
        PlantillaProceso,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="actividades",
    )
    tipos_dato = models.ManyToManyField(TipoDato, related_name="actividades", blank=True)
    destinatarios = models.ManyToManyField(Destinatario, related_name="actividades", blank=True)
    medidas_seguridad = models.ManyToManyField(MedidaSeguridad, related_name="actividades", blank=True)
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Actividad de tratamiento"
        verbose_name_plural = "Actividades de tratamiento"

    def __str__(self):
        return self.nombre
