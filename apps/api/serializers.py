from rest_framework import serializers

from apps.arco.models import SolicitudArco
from apps.auditoria.models import AuditLog
from apps.consentimiento.models import PoliticaPrivacidad, RegistroConsentimiento
from apps.rat.models import ActividadTratamiento
from apps.titulares.models import Titular


class TitularSerializer(serializers.ModelSerializer):
    """`rut` es write-only a propósito: la API nunca devuelve el RUT en
    claro en una respuesta, ni siquiera al sistema que lo acaba de enviar —
    minimización de datos (Art. 3 letra c). La correlación se hace por `id`.
    """

    rut = serializers.CharField(write_only=True)

    class Meta:
        model = Titular
        fields = ["id", "rut", "nombre", "email", "telefono", "tipo_titular", "fecha_registro"]
        read_only_fields = ["id", "fecha_registro"]

    def create(self, validated_data):
        rut = validated_data.pop("rut")
        rut_hash = Titular.hash_rut(rut)
        titular = Titular.objects.filter(rut_hash=rut_hash).first() or Titular()
        for campo, valor in validated_data.items():
            setattr(titular, campo, valor)
        titular.integracion_origen = self.context["request"].auth
        titular.rut = rut
        titular.save()
        return titular

    def update(self, instance, validated_data):
        rut = validated_data.pop("rut", None)
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        if rut:
            instance.rut = rut
        instance.save()
        return instance


class RegistroConsentimientoSerializer(serializers.ModelSerializer):
    """El titular debe existir de antemano (creado vía /titulares/): registrar
    consentimiento no auto-crea titulares con datos mínimos.
    """

    titular_rut = serializers.CharField(write_only=True)
    actividad = serializers.PrimaryKeyRelatedField(queryset=ActividadTratamiento.objects.filter(activa=True))
    politica = serializers.PrimaryKeyRelatedField(
        queryset=PoliticaPrivacidad.objects.filter(vigente=True),
        required=False,
        help_text="Si se omite, se usa la política vigente más reciente.",
    )

    class Meta:
        model = RegistroConsentimiento
        fields = [
            "id",
            "titular_rut",
            "actividad",
            "politica",
            "estado",
            "canal_origen",
            "ip_address",
            "fecha_otorgamiento",
            "fecha_revocacion",
        ]
        read_only_fields = ["id", "estado", "fecha_otorgamiento", "fecha_revocacion"]

    def create(self, validated_data):
        rut = validated_data.pop("titular_rut")
        titular = Titular.objects.filter(rut_hash=Titular.hash_rut(rut)).first()
        if titular is None:
            raise serializers.ValidationError(
                {"titular_rut": "No existe un titular con ese RUT. Regístralo primero vía /titulares/."}
            )
        politica = validated_data.pop("politica", None) or PoliticaPrivacidad.objects.filter(
            vigente=True
        ).order_by("-fecha_publicacion").first()
        if politica is None:
            raise serializers.ValidationError({"politica": "No hay ninguna política de privacidad vigente configurada."})
        request = self.context["request"]
        return RegistroConsentimiento.objects.create(
            titular=titular,
            politica=politica,
            actividad=validated_data["actividad"],
            canal_origen=validated_data.get("canal_origen", ""),
            ip_address=validated_data.get("ip_address") or request.META.get("REMOTE_ADDR"),
            integracion_origen=request.auth,
        )


class SolicitudArcoSerializer(serializers.ModelSerializer):
    titular_rut = serializers.CharField(write_only=True)

    class Meta:
        model = SolicitudArco
        fields = [
            "id",
            "titular_rut",
            "tipo_derecho",
            "estado",
            "canal_ingreso",
            "fecha_solicitud",
            "fecha_limite",
            "fecha_resolucion",
            "justificacion_rechazo",
        ]
        read_only_fields = ["id", "estado", "fecha_solicitud", "fecha_limite", "fecha_resolucion", "justificacion_rechazo"]

    def create(self, validated_data):
        rut = validated_data.pop("titular_rut")
        titular = Titular.objects.filter(rut_hash=Titular.hash_rut(rut)).first()
        if titular is None:
            raise serializers.ValidationError({"titular_rut": "No existe un titular con ese RUT."})
        return SolicitudArco.objects.create(titular=titular, **validated_data)


class AuditLogEntranteSerializer(serializers.ModelSerializer):
    """Permite que un sistema externo registre SUS PROPIOS eventos de
    auditoría en la bitácora central. No expone lectura: AuditLog es
    insert-only también desde la API.
    """

    class Meta:
        model = AuditLog
        fields = ["id", "modulo", "accion", "descripcion", "ip_address", "timestamp"]
        read_only_fields = ["id", "timestamp"]

    def create(self, validated_data):
        request = self.context["request"]
        validated_data.setdefault("ip_address", request.META.get("REMOTE_ADDR"))
        return AuditLog.objects.create(integracion_origen=request.auth, **validated_data)
