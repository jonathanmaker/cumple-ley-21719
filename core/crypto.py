"""Cifrado de campos sensibles en reposo — AES-256-GCM.

Implementa la especificación de SKL-DEV-002 §1: IV aleatorio de 12 bytes por
operación (nunca reutilizado entre registros), llave maestra fuera del código
fuente (variable de entorno FIELD_ENCRYPTION_KEY, 32 bytes en base64).

GCM protege confidencialidad E integridad: si el valor cifrado es alterado,
descifrar_campo() lanza una excepción en vez de devolver datos corruptos
silenciosamente.
"""

import base64
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class ConfiguracionCifradoError(RuntimeError):
    """FIELD_ENCRYPTION_KEY falta, no es base64 válido, o no mide 32 bytes."""


def _clave_maestra() -> bytes:
    valor = os.environ.get("FIELD_ENCRYPTION_KEY")
    if not valor:
        raise ConfiguracionCifradoError(
            "FIELD_ENCRYPTION_KEY no está definida. Generar una con: "
            'python -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"'
        )
    try:
        clave = base64.b64decode(valor)
    except Exception as exc:
        raise ConfiguracionCifradoError("FIELD_ENCRYPTION_KEY no es base64 válido.") from exc
    if len(clave) != 32:
        raise ConfiguracionCifradoError("FIELD_ENCRYPTION_KEY debe decodificar a exactamente 32 bytes (AES-256).")
    return clave


def cifrar_campo(texto_plano: str) -> str:
    """Cifra un valor con AES-256-GCM. Formato de salida: '<iv_hex>:<ciphertext_hex>'."""
    aesgcm = AESGCM(_clave_maestra())
    iv = os.urandom(12)
    cifrado = aesgcm.encrypt(iv, texto_plano.encode("utf-8"), None)
    return f"{iv.hex()}:{cifrado.hex()}"


def descifrar_campo(valor_cifrado: str) -> str:
    """Revierte cifrar_campo(). Lanza ValueError si el valor fue alterado o corrompido."""
    try:
        iv_hex, cifrado_hex = valor_cifrado.split(":", 1)
        aesgcm = AESGCM(_clave_maestra())
        resultado = aesgcm.decrypt(bytes.fromhex(iv_hex), bytes.fromhex(cifrado_hex), None)
    except (InvalidTag, ValueError) as exc:
        raise ValueError("El valor cifrado es inválido o fue alterado (falla de autenticación GCM).") from exc
    return resultado.decode("utf-8")
