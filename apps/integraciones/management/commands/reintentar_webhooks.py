from django.core.management.base import BaseCommand

from apps.integraciones.webhooks import reintentar_pendientes


class Command(BaseCommand):
    help = "Reintenta la entrega de webhooks salientes que fallaron (ver apps.integraciones.webhooks)."

    def handle(self, *args, **options):
        total = reintentar_pendientes()
        self.stdout.write(self.style.SUCCESS(f"{total} entregas de webhook reintentadas."))
