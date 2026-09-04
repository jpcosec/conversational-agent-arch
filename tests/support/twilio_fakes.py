"""Fakes del SDK de Twilio para tests sin instalar ``twilio``.

Parchea ``sys.modules`` antes de importar ``app.py`` para que
``from twilio.twiml.messaging_response import MessagingResponse`` y
``from twilio.request_validator import RequestValidator``
resuelvan a clases Python puras sin dependencia del SDK real.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Any
from xml.sax.saxutils import escape


class FakeMessagingResponse:
    """Reemplaza ``twilio.twiml.messaging_response.MessagingResponse``.

    Solo implementa ``.message(text)`` y ``__str__`` → TwiML valido.
    """

    def __init__(self) -> None:
        self._messages: list[str] = []

    def message(self, body: str, **kwargs: Any) -> None:
        self._messages.append(body)

    def __str__(self) -> str:
        inner = "".join(f"<Message>{escape(m)}</Message>" for m in self._messages)
        return f'<?xml version="1.0" encoding="UTF-8"?><Response>{inner}</Response>'


class FakeRequestValidator:
    """Reemplaza ``twilio.request_validator.RequestValidator``.

    Usa HMAC-SHA1 exactamente como Twilio (documentacion:
    https://www.twilio.com/docs/usage/security#validating-requests).

    Por testing: ``compute_signature`` recibe un ``dict`` plano (la firma que
    Twilio manda en ``X-Twilio-Signature`` no usa sorted/encoded params para
    el POST de webhook, sino el body URL-encoded completo).
    """

    def __init__(self, token: str) -> None:
        self._token = token.encode()

    def compute_signature(self, url: str, params: dict[str, str] | None = None) -> str:
        """Calcula la firma como Twilio la generaria para un webhook POST."""
        body = _urlencode_params(params or {})
        payload = url + body
        sig = hmac.new(self._token, payload.encode(), hashlib.sha1).hexdigest()
        return sig

    def validate(self, url: str, params: dict[str, str], signature: str) -> bool:
        expected = self.compute_signature(url, params)
        return hmac.compare_digest(expected, signature)


def _urlencode_params(params: dict[str, str]) -> str:
    """Codifica el body URL-encoded igual que Twilio (sin sorted + sign).

    Twilio firma el body tal cual lo recibio: los params en el orden en que
    vienen en el POST (que es el orden del formulario). Pero como ``dict``
    preserva orden en Python >= 3.7, iterar items() da el mismo orden con que
    se construyo.
    """
    if not params:
        return ""
    return "&".join(f"{_pe(k)}={_pe(v)}" for k, v in params.items())


def _pe(s: str) -> str:
    """Percent-encode igual que urllib.parse.quote_plus."""
    from urllib.parse import quote_plus
    return quote_plus(s)


def fake_twilio_module() -> dict[str, object]:
    """Retorna dict nombre_modulo → objeto_modulo para parchear sys.modules.

    Uso::

        for mod_name, mod_obj in fake_twilio_module().items():
            monkeypatch.setitem(sys.modules, mod_name, mod_obj)
    """
    import types

    twilio = types.ModuleType("twilio")

    twiml = types.ModuleType("twilio.twiml")

    messaging_response = types.ModuleType("twilio.twiml.messaging_response")
    messaging_response.MessagingResponse = FakeMessagingResponse  # type: ignore[attr-defined]

    request_validator = types.ModuleType("twilio.request_validator")
    request_validator.RequestValidator = FakeRequestValidator  # type: ignore[attr-defined]

    return {
        "twilio": twilio,
        "twilio.twiml": twiml,
        "twilio.twiml.messaging_response": messaging_response,
        "twilio.request_validator": request_validator,
    }