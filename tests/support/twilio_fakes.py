"""Dobles de Twilio que viven SOLO en pytest. No importar desde produccion.

Reemplazan ``twilio.request_validator.RequestValidator`` y
``twilio.twiml.messaging_response.MessagingResponse`` con implementaciones
deterministas en Python puro (sin dependencia del SDK twilio).
"""
from __future__ import annotations

import hashlib
import hmac
import re
from urllib.parse import urlencode


class FakeRequestValidator:
    """Version pura-Python de ``twilio.request_validator.RequestValidator``.

    Usa HMAC-SHA1 exactamente como Twilio. ``compute_signature`` genera la
    firma que Twilio enviaria; ``validate`` la verifica.
    """

    def __init__(self, token: str) -> None:
        self._token = token.encode("utf-8") if isinstance(token, str) else token

    def compute_signature(self, url: str, params: dict[str, str] | None = None) -> str:
        """Reproduce el algoritmo de firma de Twilio."""
        if params:
            # Ordenar lexicograficamente por key, luego unir key=value
            sorted_params = "".join(f"{k}{v}" for k, v in sorted(params.items()))
        else:
            sorted_params = ""
        data = url + sorted_params
        return hmac.new(self._token, data.encode("utf-8"), hashlib.sha1).hexdigest()  # nosec

    def validate(self, url: str, params: dict[str, str] | None, signature: str) -> bool:
        expected = self.compute_signature(url, params)
        return hmac.compare_digest(expected, signature)


class FakeMessagingResponse:
    """Version pura-Python de ``twilio.twiml.messaging_response.MessagingResponse``.

    Genera TwiML valido y minimo. Solo implementa ``message()`` — lo que
    el endpoint /webhooks/twilio usa realmente.
    """

    def __init__(self) -> None:
        self._messages: list[str] = []

    def message(self, body: str, to: str | None = None, from_: str | None = None) -> None:
        self._messages.append(body)

    def __str__(self) -> str:
        parts = ['<?xml version="1.0" encoding="UTF-8"?>', "<Response>"]
        for msg in self._messages:
            # Escapar caracteres XML
            safe = msg.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            parts.append(f"<Message>{safe}</Message>")
        parts.append("</Response>")
        return "".join(parts)


def fake_twilio_module() -> dict:
    """Construye un modulo ``twilio`` fake completo para inyectar via
    ``sys.modules`` o ``unittest.mock.patch.dict``.

    Uso tipico en test:

        monkeypatch.setitem(sys.modules, "twilio.request_validator", types.ModuleType("request_validator"))
        monkeypatch.setattr(sys.modules["twilio.request_validator"], "RequestValidator", FakeRequestValidator)
        monkeypatch.setitem(sys.modules, "twilio.twiml.messaging_response", types.ModuleType("messaging_response"))
        monkeypatch.setattr(sys.modules["twilio.twiml.messaging_response"], "MessagingResponse", FakeMessagingResponse)

    O usar ``patch_twilio()`` que es mas corto.
    """

    class _Module:
        pass

    base = _Module()
    base.__path__ = []
    base.request_validator = _Module()
    base.request_validator.RequestValidator = FakeRequestValidator
    base.twiml = _Module()
    base.twiml.messaging_response = _Module()
    base.twiml.messaging_response.MessagingResponse = FakeMessagingResponse
    return {
        "twilio": base,
        "twilio.request_validator": base.request_validator,
        "twilio.twiml": base.twiml,
        "twilio.twiml.messaging_response": base.twiml.messaging_response,
    }