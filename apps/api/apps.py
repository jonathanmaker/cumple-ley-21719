from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.api"
    verbose_name = "API de Integración"

    def ready(self):
        from . import schema  # noqa: F401  registra el esquema de auth en drf-spectacular
