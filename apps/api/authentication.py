from rest_framework import authentication, exceptions

from apps.integraciones.models import SistemaIntegrado


class ApiKeyAuthentication(authentication.BaseAuthentication):
    """Autentica sistemas legados vía 'Authorization: Api-Key <token>'.

    No es autenticación de usuarios finales (request.user queda vacío) —
    identifica qué SistemaIntegrado hace la llamada server-to-server. Las
    vistas y permisos de esta API deben leer el sistema desde `request.auth`,
    no desde `request.user` (ver apps.api.permissions.TieneScope).
    """

    keyword = "Api-Key"

    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header:
            return None
        try:
            scheme, token = header.split(" ", 1)
        except ValueError:
            raise exceptions.AuthenticationFailed("Encabezado Authorization mal formado.")
        if scheme != self.keyword:
            return None
        sistema = SistemaIntegrado.verificar_api_key(token.strip())
        if sistema is None:
            raise exceptions.AuthenticationFailed("API key inválida, revocada o inexistente.")
        return (None, sistema)

    def authenticate_header(self, request):
        return self.keyword
