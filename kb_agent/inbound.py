"""Servicio de mensajes entrantes por canal externo (Twilio WhatsApp/SMS).

Es la capa entre el webhook HTTP y ``Orchestrator.handle_turn``: normaliza el
remitente a un ``external_id`` con canal, persiste el mensaje como
``InboundMessage`` (el *source* del turno), resuelve el usuario, corre el turno
y deja el rastro (usuario, conversacion, turno, respuesta) en la misma fila.

Idempotencia: Twilio reintenta el webhook si no recibe respuesta en 15 s. Un
reintento trae el mismo ``MessageSid``; el UNIQUE de ``inbound_messages`` lo
detecta y se devuelve la respuesta ya guardada (o una respuesta vacia si el
turno original sigue corriendo) en vez de correr un segundo turno.

Dos modos de respuesta (``frontends/chat/app.py`` elige):

* **sync**: el webhook espera el turno y responde TwiML con el texto. Solo
  sirve si el turno cabe en los 15 s de Twilio; un turno con LLM y embeddings
  medido en local tarda 20-35 s.
* **async**: el webhook persiste el mensaje, responde ``<Response/>`` al
  instante y el turno corre en background; al terminar, la respuesta sale por
  la API REST de Twilio (``sender``). El ``MessageSid`` del mensaje saliente
  queda en ``reply_provider_message_id``.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from sqlalchemy.exc import IntegrityError

from kb_agent.models_sql.inbound import InboundMessage, InboundStatus
from kb_agent.orchestrator import Orchestrator, canonical_phone

log = logging.getLogger(__name__)

PROVIDER_TWILIO = "twilio"
#: Canal asumido cuando el remitente viene sin prefijo. Twilio manda los SMS
#: con ``From=+569...`` pelado y los WhatsApp con ``From=whatsapp:+569...``.
DEFAULT_BARE_CHANNEL = "sms"

#: Envia un mensaje saliente: ``(to, from_, body) -> id del mensaje en el
#: proveedor`` (o None si el proveedor no devuelve id).
Sender = Callable[[str, str, str], str | None]


def normalize_sender(raw_from: str, *, bare_channel: str = DEFAULT_BARE_CHANNEL) -> tuple[str, str]:
    """Remitente del proveedor -> ``(external_id, channel)``.

    * ``whatsapp:+56 9 1234 5678`` -> ``("whatsapp:+56912345678", "whatsapp")``
    * ``+56912345678``             -> ``("sms:+56912345678", "sms")``
    * ``messenger:12345``          -> ``("messenger:+12345", "messenger")``

    El ``external_id`` siempre lleva prefijo de canal: asi
    ``channel_from_external_id`` del orquestador lo reconoce y no cae en
    ``unknown`` (que es lo que pasaba con los SMS pelados), y con
    ``identity_key='phone'`` el telefono canonico unifica a la persona entre
    whatsapp y sms.
    """
    raw = (raw_from or "").strip()
    prefix, sep, rest = raw.partition(":")
    if sep and prefix and " " not in prefix and not prefix.startswith("+"):
        channel, ident = prefix.lower(), rest.strip()
    else:
        channel, ident = bare_channel, raw
    ident = canonical_phone(ident) or ident
    return f"{channel}:{ident}", channel


def twilio_rest_sender(account_sid: str, auth_token: str) -> Sender:
    """Sender real sobre ``twilio.rest.Client`` (import perezoso: los tests
    no necesitan el SDK)."""
    from twilio.rest import Client

    client = Client(account_sid, auth_token)

    def _send(to: str, from_: str, body: str) -> str | None:
        msg = client.messages.create(to=to, from_=from_, body=body)
        return getattr(msg, "sid", None)

    return _send


def _provider_message_id(form: Mapping[str, str]) -> str | None:
    return (form.get("MessageSid") or form.get("SmsMessageSid") or "").strip() or None


@dataclass(slots=True)
class InboundResult:
    reply_text: str
    inbound_id: int | None
    duplicate: bool = False
    #: True cuando el turno quedo corriendo en background (modo async).
    deferred: bool = False
    turn: dict[str, Any] | None = None


class InboundService:
    """Recibe el form del webhook, persiste el mensaje y corre el turno."""

    def __init__(
        self,
        orchestrator: Orchestrator,
        *,
        provider: str = PROVIDER_TWILIO,
        sender: Sender | None = None,
    ) -> None:
        self.orch = orchestrator
        self.provider = provider
        self.sender = sender

    # ── persistencia ─────────────────────────────────────────────────────
    def record(self, form: Mapping[str, str]) -> InboundMessage | None:
        """Normaliza el remitente, resuelve el usuario e inserta la fila.

        None si ya existia un mensaje con el mismo id de proveedor (reintento).
        La fila devuelta esta desvinculada de la sesion (``expunge``).
        """
        external_id, channel = normalize_sender(form.get("From", ""))
        try:
            num_media = int(form.get("NumMedia") or 0)
        except ValueError:
            num_media = 0
        session = self.orch.SessionLocal()
        try:
            user = self.orch.ensure_user(session, external_id, channel=channel)
            row = InboundMessage(
                provider=self.provider,
                provider_message_id=_provider_message_id(form),
                channel=channel,
                external_id=external_id,
                phone=canonical_phone(external_id.partition(":")[2]),
                to=form.get("To") or None,
                body=(form.get("Body") or "").strip(),
                profile_name=form.get("ProfileName") or None,
                num_media=num_media,
                payload=dict(form),
                user_id=user.id,
                status=InboundStatus.RECEIVED,
            )
            session.add(row)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                return None
            session.refresh(row)
            session.expunge(row)
            return row
        finally:
            session.close()

    def existing(self, form: Mapping[str, str]) -> InboundMessage | None:
        msg_id = _provider_message_id(form)
        if msg_id is None:
            return None
        session = self.orch.SessionLocal()
        try:
            row = (
                session.query(InboundMessage)
                .filter_by(provider=self.provider, provider_message_id=msg_id)
                .one_or_none()
            )
            if row is not None:
                session.expunge(row)
            return row
        finally:
            session.close()

    def _finish(
        self,
        inbound_id: int,
        *,
        turn: dict[str, Any] | None,
        error: str | None = None,
        reply_provider_message_id: str | None = None,
    ) -> None:
        session = self.orch.SessionLocal()
        try:
            row = session.get(InboundMessage, inbound_id)
            if row is None:
                return
            if turn is not None:
                row.status = InboundStatus.REPLIED
                row.reply_text = turn.get("reply_text") or turn.get("reply") or ""
                row.turn_id = turn.get("turn_id")
                row.conversation_id = turn.get("conversation_id")
                row.user_id = turn.get("user_id") or row.user_id
                row.reply_provider_message_id = reply_provider_message_id
                row.replied_at = datetime.now(timezone.utc)
            else:
                row.status = InboundStatus.FAILED
                row.error = error
            session.commit()
        finally:
            session.close()

    # ── turno ────────────────────────────────────────────────────────────
    def run_turn(self, row: InboundMessage) -> dict[str, Any]:
        """Corre el turno del mensaje ya persistido y cierra la fila."""
        try:
            turn = self.orch.handle_turn(
                external_id=row.external_id, message=row.body, channel=row.channel
            )
        except Exception as exc:  # noqa: BLE001 - se registra y se propaga
            self._finish(row.id, turn=None, error=f"{type(exc).__name__}: {exc}")
            raise
        self._finish(row.id, turn=turn)
        return turn

    def run_turn_and_send(self, row: InboundMessage) -> None:
        """Modo async: corre el turno y manda la respuesta por el proveedor.

        Pensado para un background task: nunca levanta, deja el error en la
        fila (``status=failed``, ``error``) y en el log.
        """
        try:
            turn = self.run_turn(row)
        except Exception:  # noqa: BLE001
            log.exception("inbound %s: el turno fallo", row.id)
            return
        reply = turn.get("reply_text") or turn.get("reply") or ""
        if not reply or self.sender is None or not row.to:
            return
        try:
            sent_id = self.sender(row.external_id.partition(":")[2] if row.channel == "sms"
                                  else row.external_id, row.to, reply)
        except Exception as exc:  # noqa: BLE001
            log.exception("inbound %s: fallo el envio de la respuesta", row.id)
            self._finish(row.id, turn=None, error=f"send: {type(exc).__name__}: {exc}")
            return
        self._finish(row.id, turn=turn, reply_provider_message_id=sent_id)

    # ── entrada (modo sync) ──────────────────────────────────────────────
    def receive(self, form: Mapping[str, str]) -> InboundResult:
        """Persiste y corre el turno en linea; devuelve el texto a responder."""
        row = self.record(form)
        if row is None:
            prev = self.existing(form)
            # Reintento: si el turno original ya respondio, repetimos esa
            # respuesta; si sigue corriendo, respuesta vacia (Twilio no
            # reenvia nada y el original entregara la suya).
            return InboundResult(
                reply_text=(prev.reply_text or "") if prev is not None else "",
                inbound_id=prev.id if prev is not None else None,
                duplicate=True,
            )
        turn = self.run_turn(row)
        return InboundResult(
            reply_text=turn.get("reply_text") or turn.get("reply") or "",
            inbound_id=row.id,
            turn=turn,
        )
