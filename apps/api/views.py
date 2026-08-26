from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.arco.models import SolicitudArco
from apps.auditoria.models import AuditLog
from apps.consentimiento.models import RegistroConsentimiento
from apps.integraciones.models import WebhookSuscripcion
from apps.integraciones.webhooks import disparar_webhook
from apps.titulares.models import Titular

from .serializers import (
    AuditLogEntranteSerializer,
    RegistroConsentimientoSerializer,
    SolicitudArcoSerializer,
    TitularSerializer,
)


def _auditar(request, modulo, accion, descripcion):
    """Cada escritura hecha vía API queda en el mismo AuditLog inmutable que
    usa el resto de la plataforma (DoD: 'Registro de Auditoría', chef_agent.md §4).
    """
    AuditLog.objects.create(
        integracion_origen=request.auth,
        modulo=modulo,
        accion=accion,
        descripcion=descripcion,
        ip_address=request.META.get("REMOTE_ADDR"),
    )


class TitularViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """No expone destrucción vía API a propósito: la eliminación de un
    titular pasa siempre por el flujo de Solicitud ARCO (supresión), nunca
    por un DELETE directo desde un sistema externo.
    """

    queryset = Titular.objects.all().order_by("-fecha_registro")
    serializer_class = TitularSerializer

    def get_permissions(self):
        self.scope_requerido = "titulares:read" if self.action in ("list", "retrieve") else "titulares:write"
        return super().get_permissions()

    def perform_create(self, serializer):
        titular = serializer.save()
        _auditar(self.request, "API", AuditLog.Accion.MODIFICACION, f"Sistema externo registró/actualizó titular {titular.id}")

    def perform_update(self, serializer):
        titular = serializer.save()
        _auditar(self.request, "API", AuditLog.Accion.MODIFICACION, f"Sistema externo actualizó titular {titular.id}")


class RegistroConsentimientoViewSet(
    mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet
):
    queryset = RegistroConsentimiento.objects.all().order_by("-fecha_otorgamiento")
    serializer_class = RegistroConsentimientoSerializer

    def get_permissions(self):
        self.scope_requerido = "consentimiento:read" if self.action in ("list", "retrieve") else "consentimiento:write"
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset()
        titular_rut = self.request.query_params.get("titular_rut")
        if titular_rut:
            qs = qs.filter(titular__rut_hash=Titular.hash_rut(titular_rut))
        return qs

    def perform_create(self, serializer):
        registro = serializer.save()
        _auditar(self.request, "API", AuditLog.Accion.MODIFICACION, f"Sistema externo registró consentimiento {registro.id}")

    @action(detail=True, methods=["post"], url_path="revocar")
    def revocar(self, request, pk=None):
        registro = self.get_object()
        registro.estado = RegistroConsentimiento.Estado.REVOCADO
        registro.fecha_revocacion = timezone.now()
        registro.save(update_fields=["estado", "fecha_revocacion"])
        _auditar(request, "API", AuditLog.Accion.MODIFICACION, f"Sistema externo revocó consentimiento {registro.id}")
        disparar_webhook(
            WebhookSuscripcion.Evento.CONSENTIMIENTO_REVOCADO,
            {
                "consentimiento_id": str(registro.id),
                "titular_id": str(registro.titular_id),
                "actividad_id": str(registro.actividad_id),
                "fecha_revocacion": registro.fecha_revocacion.isoformat(),
            },
        )
        return Response(RegistroConsentimientoSerializer(registro).data)


class SolicitudArcoViewSet(
    mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet
):
    queryset = SolicitudArco.objects.all().order_by("-fecha_solicitud")
    serializer_class = SolicitudArcoSerializer

    def get_permissions(self):
        self.scope_requerido = "arco:read" if self.action in ("list", "retrieve") else "arco:write"
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset()
        titular_rut = self.request.query_params.get("titular_rut")
        if titular_rut:
            qs = qs.filter(titular__rut_hash=Titular.hash_rut(titular_rut))
        return qs

    def perform_create(self, serializer):
        solicitud = serializer.save()
        _auditar(
            self.request,
            "API",
            AuditLog.Accion.MODIFICACION,
            f"Sistema externo creó solicitud ARCO {solicitud.id} ({solicitud.tipo_derecho})",
        )


class AuditLogEntranteViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """Solo inserción — AuditLog nunca se lee ni se modifica vía API."""

    queryset = AuditLog.objects.none()
    serializer_class = AuditLogEntranteSerializer
    scope_requerido = "auditoria:write"
