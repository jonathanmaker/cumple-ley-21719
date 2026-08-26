from rest_framework.throttling import SimpleRateThrottle


class SistemaIntegradoRateThrottle(SimpleRateThrottle):
    """Limita por SistemaIntegrado autenticado, no por IP — server-to-server,
    varias integraciones pueden compartir la misma IP saliente (ej. detrás
    de un NAT corporativo) y no deben compartir el mismo cupo.
    """

    scope = "sistema_integrado"

    def get_cache_key(self, request, view):
        sistema = request.auth
        if sistema is None:
            return None
        return self.cache_format % {"scope": self.scope, "ident": sistema.pk}
