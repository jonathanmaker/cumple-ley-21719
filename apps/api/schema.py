from drf_spectacular.extensions import OpenApiAuthenticationExtension


class ApiKeyAuthenticationScheme(OpenApiAuthenticationExtension):
    """Le enseña a drf-spectacular cómo documentar ApiKeyAuthentication en
    /api/v1/docs/, para que un integrador externo vea el encabezado
    requerido sin tener que leer el código fuente.
    """

    target_class = "apps.api.authentication.ApiKeyAuthentication"
    name = "ApiKeyAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": "Formato: 'Api-Key <token>' (ver SistemaIntegrado.crear_con_api_key).",
        }
