from rest_framework.routers import DefaultRouter

from .views import (
    AuditLogEntranteViewSet,
    RegistroConsentimientoViewSet,
    SolicitudArcoViewSet,
    TitularViewSet,
)

router = DefaultRouter()
router.register("titulares", TitularViewSet, basename="titular")
router.register("consentimientos", RegistroConsentimientoViewSet, basename="consentimiento")
router.register("solicitudes-arco", SolicitudArcoViewSet, basename="solicitud-arco")
router.register("auditoria", AuditLogEntranteViewSet, basename="auditoria")

urlpatterns = router.urls
