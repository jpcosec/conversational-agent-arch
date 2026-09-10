"""Endpoint Twilio probado con fakes puramente Python (sin SDK twilio).

El mock vive exclusivamente en ``tests/support/twilio_fakes.py`` y se inyecta
via ``monkeypatch.setitem(sys.modules, ...)`` antes de importar ``app.py``.
Produccion nunca ve estos fakes.
"""
from __future__ import annotations

import sys

import pytest
from fastapi.testclient import TestClient

from tests.support.twilio_fakes import (
    FakeMessagingResponse,
    FakeRequestValidator,
    fake_twilio_module,
)

TOKEN = "twilio-test-token"
FAKE_TWILIO = fake_twilio_module()


def _patch_twilio(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reemplaza los imports de twilio en sys.modules ANTES de que app.py cargue.

    Si ``app.py`` ya fue importado (y por tanto ``twilio.request_validator``
    ya esta vinculado), parchea tambien los atributos de los modulos reales.
    """
    for mod_name, mod_obj in FAKE_TWILIO.items():
        if mod_name in sys.modules:
            # Ya importado por otro test: sobreescribir atributo por atributo
            existing = sys.modules[mod_name]
            for attr in dir(mod_obj):
                if not attr.startswith("_"):
                    setattr(existing, attr, getattr(mod_obj, attr))
        else:
            monkeypatch.setitem(sys.modules, mod_name, mod_obj)


@pytest.fixture
def fake_twilio_app(tmp_path: Path, negocio_kb: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """App con Twilio completamente fake — sin instalar ``twilio``.

    Parchea sys.modules ANTES de importar app.py para que ``from twilio.xxx
    import Y`` resuelva a los fakes, no al SDK real.
    """
    # Patch MUST happen before any import of app.py or twilio
    for mod_name, mod_obj in FAKE_TWILIO.items():
        monkeypatch.setitem(sys.modules, mod_name, mod_obj)
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", TOKEN)
    # Modo sync por defecto en estos tests (sin ACCOUNT_SID no hay REST).
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("TWILIO_REPLY_MODE", raising=False)

    from kb_agent.project_config import load_project_config
    from kb_agent.tools import load_tool_handlers
    from tests.support.fakes import offline_orchestrator
    import frontends.chat.app as app_module
    from frontends.chat.app import create_app

    # Si app.py ya fue importado por otro modulo de tests (test_chat_api lo
    # importa a nivel de modulo con el SDK real), sus nombres ya estan
    # vinculados a las clases reales y parchear sys.modules no las alcanza:
    # se rebindean los nombres del modulo de la app a los fakes.
    monkeypatch.setattr(app_module, "RequestValidator", FakeRequestValidator)
    monkeypatch.setattr(app_module, "MessagingResponse", FakeMessagingResponse)

    db = tmp_path / "chat.sqlite"
    cfg = load_project_config(mode="test", env={"CHAT_DB": str(db), "PROFILING_DB": str(db)})
    orch = offline_orchestrator(
        cfg.kb_root,
        cfg.chat_db_url,
        tool_handlers=load_tool_handlers(cfg.tool_handlers),
        identity_key=cfg.identity_key,  # mismo criterio que Orchestrator.from_config
    )

    with TestClient(create_app(cfg, orch)) as c:
        yield c
    orch.close()


# ── Helper ────────────────────────────────────────────────────────────────────

def _post(client: TestClient, form: dict, signature: str):
    return client.post("/webhooks/twilio", data=form, headers={"X-Twilio-Signature": signature})


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_valid_signature_runs_turn_and_replies_twiml(fake_twilio_app: TestClient) -> None:
    form = {"From": "whatsapp:+56912345678", "To": "whatsapp:+14155238886",
            "Body": "  que pizzas tienen?  ", "MessageSid": "SM1"}
    url = str(fake_twilio_app.base_url) + "/webhooks/twilio"
    sig = FakeRequestValidator(TOKEN).compute_signature(url, form)
    res = _post(fake_twilio_app, form, sig)

    assert res.status_code == 200
    assert res.headers["content-type"].startswith("application/xml")
    assert "<Message>[nl]" in res.text
    assert "Markdown" not in res.text  # TwiML, no markdown

    # usuario creado con canal derivado del prefijo whatsapp:
    users = {u["external_id"]: u["channel"]
             for u in fake_twilio_app.get("/api/profiles").json()["users"]}
    assert users["whatsapp:+56912345678"] == "whatsapp"


def test_invalid_signature_is_rejected(fake_twilio_app: TestClient) -> None:
    calls_before = len(fake_twilio_app.app.state.orchestrator.conversador.calls)
    res = _post(fake_twilio_app, {"From": "whatsapp:+1", "Body": "hola"}, "firma-invalida")

    assert res.status_code == 403
    assert res.json() == {"detail": "invalid twilio signature"}
    assert len(fake_twilio_app.app.state.orchestrator.conversador.calls) == calls_before


def test_unconfigured_returns_503(fake_twilio_app: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    res = _post(fake_twilio_app, {"From": "whatsapp:+1", "Body": "hola"}, "x")

    assert res.status_code == 503
    assert "twilio not configured" in res.json()["detail"]


def test_whatsapp_sms_channel_resolved_from_prefix(fake_twilio_app: TestClient) -> None:
    """whatsapp:+569... y sms:+569... se mapean a canales distintos."""
    url = str(fake_twilio_app.base_url) + "/webhooks/twilio"
    v = FakeRequestValidator(TOKEN)
    for prefix, channel in [("whatsapp:+569111", "whatsapp"), ("sms:+569222", "sms")]:
        form = {"From": prefix, "Body": "hola"}
        sig = v.compute_signature(url, form)
        res = _post(fake_twilio_app, form, sig)
        assert res.status_code == 200

    users = {u["external_id"]: u["channel"]
             for u in fake_twilio_app.get("/api/profiles").json()["users"]}
    assert users.get("whatsapp:+569111") == "whatsapp"
    assert users.get("sms:+569222") == "sms"


def test_twilio_fake_str_empty_response() -> None:
    """FakeMessagingResponse sin messages produce TwiML valido."""
    r = FakeMessagingResponse()
    assert str(r) == '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'


def test_twilio_fake_escapes_xml() -> None:
    r = FakeMessagingResponse()
    r.message("<script>alert(1)</script> & <test>")
    assert "&lt;script&gt;" in str(r)
    assert "&amp;" in str(r)


def test_twilio_fake_request_validator_roundtrip() -> None:
    url = "https://example.com/twilio"
    params = {"From": "+1", "Body": "test"}
    v = FakeRequestValidator("my-token")
    sig = v.compute_signature(url, params)
    assert v.validate(url, params, sig)
    assert not v.validate(url, params, "bad")
    assert not v.validate(url + "/other", params, sig)


def test_twilio_fake_request_validator_no_params() -> None:
    v = FakeRequestValidator("tok")
    sig = v.compute_signature("https://example.com/twilio")
    assert v.validate("https://example.com/twilio", {}, sig)
    assert not v.validate("https://example.com/twilio", {"x": "y"}, sig)

# ── InboundService: source, usuario, idempotencia ─────────────────────────────

def _signed_post(client: TestClient, form: dict):
    url = str(client.base_url) + "/webhooks/twilio"
    return _post(client, form, FakeRequestValidator(TOKEN).compute_signature(url, form))


def _inbound_rows(client: TestClient) -> list:
    from kb_agent.models_sql.inbound import InboundMessage
    orch = client.app.state.orchestrator
    with orch.SessionLocal() as s:
        rows = s.query(InboundMessage).order_by(InboundMessage.id).all()
        s.expunge_all()
        return rows


def test_bare_sms_from_is_normalized_to_sms_channel(fake_twilio_app: TestClient) -> None:
    """Twilio manda los SMS con From=+569... pelado: antes caia en canal 'unknown'."""
    res = _signed_post(fake_twilio_app, {"From": "+56 9 8765 4321", "To": "+56229149113",
                                         "Body": "hola", "MessageSid": "SMsms1"})
    assert res.status_code == 200

    users = {u["external_id"]: u["channel"]
             for u in fake_twilio_app.get("/api/profiles").json()["users"]}
    assert users == {"sms:+56987654321": "sms"}

    (row,) = _inbound_rows(fake_twilio_app)
    assert (row.provider, row.provider_message_id) == ("twilio", "SMsms1")
    assert (row.channel, row.external_id, row.phone) == ("sms", "sms:+56987654321", "+56987654321")
    assert row.to == "+56229149113"
    assert row.status.value == "replied"
    assert row.user_id is not None and row.conversation_id is not None and row.turn_id
    assert row.reply_text.startswith("[nl]")
    assert row.payload["Body"] == "hola"


def test_retry_with_same_message_sid_does_not_run_second_turn(fake_twilio_app: TestClient) -> None:
    """Twilio reintenta el webhook (timeout 15 s) con el MISMO MessageSid."""
    form = {"From": "whatsapp:+56911111111", "To": "whatsapp:+14155238886",
            "Body": "que pizzas tienen?", "MessageSid": "SMdup1", "ProfileName": "JP"}
    conv = fake_twilio_app.app.state.orchestrator.conversador
    first = _signed_post(fake_twilio_app, form)
    calls_after_first = len(conv.calls)
    second = _signed_post(fake_twilio_app, form)

    assert first.status_code == second.status_code == 200
    assert second.text == first.text                      # misma respuesta, no un turno nuevo
    assert len(conv.calls) == calls_after_first           # el LLM no volvio a correr
    rows = _inbound_rows(fake_twilio_app)
    assert len(rows) == 1 and rows[0].profile_name == "JP"

    from kb_agent.models_sql.turns import Turns
    with fake_twilio_app.app.state.orchestrator.SessionLocal() as s:
        assert s.query(Turns).count() == 1


def test_same_phone_whatsapp_and_sms_is_one_user(fake_twilio_app: TestClient) -> None:
    """identity_key='phone' (project.config.yaml): la persona es una, los external_id son alias."""
    from kb_agent.models_sql.identity import Users
    assert fake_twilio_app.app.state.orchestrator.identity_key == "phone"

    _signed_post(fake_twilio_app, {"From": "whatsapp:+56922222222", "Body": "hola", "MessageSid": "SMa"})
    _signed_post(fake_twilio_app, {"From": "+56922222222", "Body": "hola de nuevo", "MessageSid": "SMb"})

    with fake_twilio_app.app.state.orchestrator.SessionLocal() as s:
        users = s.query(Users).all()
        assert len(users) == 1 and users[0].phone == "+56922222222"
        user_id = users[0].id
    rows = _inbound_rows(fake_twilio_app)
    assert [r.channel for r in rows] == ["whatsapp", "sms"]
    assert {r.user_id for r in rows} == {user_id}


# ── modo async: <Response/> al instante, respuesta por REST ───────────────────

def test_async_mode_replies_empty_twiml_and_sends_via_rest(
    fake_twilio_app: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Twilio corta a los 15 s: con ACCOUNT_SID el webhook responde vacio y el
    turno corre en background; la respuesta sale por el sender (REST)."""
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACtest")
    sent: list[tuple[str, str, str]] = []

    def fake_sender(to: str, from_: str, body: str) -> str:
        sent.append((to, from_, body))
        return "SMout1"

    fake_twilio_app.app.state.twilio_sender = fake_sender
    try:
        form = {"From": "whatsapp:+56933333333", "To": "whatsapp:+14155238886",
                "Body": "que pizzas tienen?", "MessageSid": "SMasync1"}
        res = _signed_post(fake_twilio_app, form)          # TestClient corre los background tasks
        assert res.status_code == 200
        assert "<Message>" not in res.text                # vacio: la respuesta no va en el TwiML

        assert len(sent) == 1
        to, from_, body = sent[0]
        assert (to, from_) == ("whatsapp:+56933333333", "whatsapp:+14155238886")
        assert body.startswith("[nl]")

        (row,) = _inbound_rows(fake_twilio_app)
        assert row.status.value == "replied"
        assert row.reply_text == body
        assert row.reply_provider_message_id == "SMout1"
        assert row.turn_id

        # Reintento del mismo MessageSid: ni turno ni envio nuevos.
        res2 = _signed_post(fake_twilio_app, form)
        assert res2.status_code == 200 and len(sent) == 1
        assert len(_inbound_rows(fake_twilio_app)) == 1
    finally:
        fake_twilio_app.app.state.twilio_sender = None


def test_async_mode_sms_sends_to_bare_number(
    fake_twilio_app: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Por SMS el ``to`` del envio va sin prefijo de canal."""
    monkeypatch.setenv("TWILIO_REPLY_MODE", "async")
    sent: list[tuple[str, str, str]] = []
    fake_twilio_app.app.state.twilio_sender = lambda to, from_, body: sent.append((to, from_, body)) or None
    try:
        res = _signed_post(fake_twilio_app, {"From": "+56944444444", "To": "+56229149113",
                                             "Body": "hola", "MessageSid": "SMasync2"})
        assert res.status_code == 200
        assert sent and sent[0][:2] == ("+56944444444", "+56229149113")
        (row,) = _inbound_rows(fake_twilio_app)
        assert row.status.value == "replied" and row.reply_provider_message_id is None
    finally:
        fake_twilio_app.app.state.twilio_sender = None
