"""Aplica el principio de limitación de conservación (Art. 3 letra d):
anonimiza titulares cuyo consentimiento fue revocado y ya venció el plazo de
conservación de la actividad correspondiente, siempre que no tengan otro
consentimiento OTORGADO vigente para otra actividad.

Alcance deliberadamente acotado en este MVP: solo cubre "consentimiento
revocado + plazo vencido" (Art. 7, letra b — revocación sin otra base legal).
Relaciones que terminan por otras vías (fin de contrato, término de relación
laboral, vencimiento de una obligación legal) requieren una señal de negocio
que el modelo de datos actual no captura todavía (ej. una fecha de término de
relación por actividad) — no se inventa esa lógica aquí (R-ARN-002); queda
como trabajo futuro explícito, no como un caso silenciosamente ignorado.

Pensado para correr periódicamente vía cron externo del hosting (ej. una
entrada de cron del sistema operativo o del proveedor de VPS ejecutando
`docker compose exec web python manage.py aplicar_retencion`) — no se agrega
un scheduler propio para no sumar otro servicio a la pila.
"""

import datetime
import secrets

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.auditoria.models import AuditLog
from apps.consentimiento.models import RegistroConsentimiento
from apps.integraciones.models import WebhookSuscripcion
from apps.integraciones.webhooks import disparar_webhook


class Command(BaseCommand):
    help = "Anonimiza titulares con consentimiento revocado y plazo de conservación vencido."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true", help="Solo informa qué se anonimizaría, sin ejecutar cambios."
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        ahora = timezone.now()

        candidatos = RegistroConsentimiento.objects.filter(
            estado=RegistroConsentimiento.Estado.REVOCADO,
            fecha_revocacion__isnull=False,
        ).select_related("titular", "actividad")

        anonimizados = 0
        for registro in candidatos:
            titular = registro.titular
            if titular.nombre == "ANONIMIZADO":
                continue

            limite = registro.fecha_revocacion + datetime.timedelta(
                days=30 * registro.actividad.plazo_conservacion_meses
            )
            if ahora < limite:
                continue

            tiene_otro_consentimiento_vigente = RegistroConsentimiento.objects.filter(
                titular=titular, estado=RegistroConsentimiento.Estado.OTORGADO
            ).exists()
            if tiene_otro_consentimiento_vigente:
                continue

            anonimizados += 1
            if dry_run:
                self.stdout.write(
                    f"[dry-run] anonimizaría titular {titular.id} (actividad '{registro.actividad.nombre}', "
                    f"vencido desde {limite.date()})"
                )
                continue

            # rut_hash también se reemplaza: un hash SHA-256 de un RUT (baja
            # entropía, ~8 dígitos) es vulnerable a fuerza bruta/diccionario,
            # así que dejarlo intacto filtraría la identidad igual.
            titular.rut_hash = secrets.token_hex(32)
            titular.rut_cifrado = ""
            titular.nombre = "ANONIMIZADO"
            titular.email = ""
            titular.telefono = ""
            titular.save(update_fields=["rut_hash", "rut_cifrado", "nombre", "email", "telefono"])

            AuditLog.objects.create(
                modulo="RAT",
                accion=AuditLog.Accion.ANONIMIZACION,
                descripcion=(
                    f"Titular {titular.id} anonimizado por vencimiento del plazo de conservación "
                    f"de la actividad '{registro.actividad.nombre}'."
                ),
            )
            disparar_webhook(
                WebhookSuscripcion.Evento.PURGA_EJECUTADA,
                {
                    "titular_id": str(titular.id),
                    "actividad_id": str(registro.actividad_id),
                    "tipo_accion": "ANONIMIZACION",
                },
            )

        verbo = "Se anonimizarían" if dry_run else "Se anonimizaron"
        self.stdout.write(self.style.SUCCESS(f"{verbo} {anonimizados} titulares."))
