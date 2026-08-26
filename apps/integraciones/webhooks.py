"""Despacho de webhooks salientes a los sistemas integrados suscritos.

Síncrono y best-effort para el MVP (sin cola de tareas como Celery, para no
sumar otro servicio a la pila — ver decisión de arquitectura en memoria de
proyecto). Un envío fallido nunca debe romper el flujo principal que lo
disparó (ej. resolver una solicitud ARCO no puede fallar porque el ERP del
cliente esté caído): queda registrado en WebhookEntrega con entregado=False
para que `manage.py reintentar_webhooks` lo reintente después.
"""

import hashlib
import hmac
import json

import requests

from .models import SistemaIntegrado, WebhookEntrega, WebhookSuscripcion

TIMEOUT_SEGUNDOS = 5
MAX_INTENTOS = 5


def _firmar(secreto: str, cuerpo: bytes) -> str:
    return hmac.new(secreto.encode("utf-8"), cuerpo, hashlib.sha256).hexdigest()


def _enviar(entrega: WebhookEntrega) -> None:
    suscripcion = entrega.suscripcion
    cuerpo = json.dumps(entrega.payload).encode("utf-8")
    firma = _firmar(suscripcion.secreto, cuerpo)
    try:
        respuesta = requests.post(
            suscripcion.url_destino,
            data=cuerpo,
            headers={
                "Content-Type": "application/json",
                "X-Cumple21719-Evento": entrega.evento,
                "X-Cumple21719-Firma": firma,
            },
            timeout=TIMEOUT_SEGUNDOS,
        )
        entrega.status_code = respuesta.status_code
        entrega.entregado = 200 <= respuesta.status_code < 300
    except requests.RequestException:
        entrega.status_code = None
        entrega.entregado = False
    entrega.intentos += 1
    entrega.save(update_fields=["status_code", "entregado", "intentos"])


def disparar_webhook(evento: str, payload: dict) -> list[WebhookEntrega]:
    """Notifica a TODOS los sistemas integrados activos suscritos a `evento`,
    sin importar cuál sistema originó el dato — si dos sistemas legados de la
    misma organización comparten un titular, ambos deben enterarse cuando su
    consentimiento se revoca o sus datos se purgan, no solo el que lo creó.
    """
    entregas = []
    suscripciones = WebhookSuscripcion.objects.filter(
        activo=True, sistema_integrado__estado=SistemaIntegrado.Estado.ACTIVO
    ).select_related("sistema_integrado")
    for suscripcion in suscripciones:
        if evento not in suscripcion.eventos_suscritos:
            continue
        entrega = WebhookEntrega.objects.create(suscripcion=suscripcion, evento=evento, payload=payload)
        _enviar(entrega)
        entregas.append(entrega)
    return entregas


def reintentar_pendientes(max_intentos: int = MAX_INTENTOS) -> int:
    """Reintenta entregas no exitosas que no superaron max_intentos. Pensado
    para correr periódicamente (cron externo o scheduler del hosting llamando
    a `manage.py reintentar_webhooks` — no se agrega un scheduler propio para
    no sumar otro servicio a la pila).
    """
    pendientes = WebhookEntrega.objects.filter(entregado=False, intentos__lt=max_intentos)
    contador = 0
    for entrega in pendientes:
        _enviar(entrega)
        contador += 1
    return contador
