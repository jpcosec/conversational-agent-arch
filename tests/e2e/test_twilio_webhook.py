from __future__ import annotations

import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from twilio.request_validator import RequestValidator

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

import kb_chat_ui.server as server


@pytest.fixture()
def client() -> TestClient:
    return TestClient(server.app)


def _signature(url: str, form: dict[str, str], token: str) -> str:
    return RequestValidator(token).compute_signature(url, form)


def test_twilio_webhook_translates_form_to_handle_turn_and_replies_twiml(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    token = "twilio-test-token"
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", token)

    seen: dict[str, str] = {}

    def fake_handle_turn(*, external_id: str, message: str, scenario: str | None = None) -> dict:
        seen["external_id"] = external_id
        seen["message"] = message
        seen["scenario"] = str(scenario)
        return {"reply_text": "Hola desde runtime"}

    monkeypatch.setattr(server.orchestrator, "handle_turn", fake_handle_turn)

    form = {
        "From": "whatsapp:+56912345678",
        "To": "whatsapp:+14155238886",
        "Body": "  Quiero reservar una mesa  ",
        "MessageSid": "SM123",
    }
    url = str(client.base_url) + "/webhooks/twilio"
    signature = _signature(url, form, token)

    response = client.post(
        "/webhooks/twilio",
        data=form,
        headers={"X-Twilio-Signature": signature},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    assert "<Message>Hola desde runtime</Message>" in response.text
    assert seen == {
        "external_id": "whatsapp:+56912345678",
        "message": "Quiero reservar una mesa",
        "scenario": "None",
    }


def test_twilio_webhook_rejects_invalid_signature(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "twilio-test-token")

    called = False

    def fake_handle_turn(*, external_id: str, message: str, scenario: str | None = None) -> dict:
        nonlocal called
        called = True
        return {"reply_text": "no deberia llamarse"}

    monkeypatch.setattr(server.orchestrator, "handle_turn", fake_handle_turn)

    response = client.post(
        "/webhooks/twilio",
        data={
            "From": "whatsapp:+56912345678",
            "To": "whatsapp:+14155238886",
            "Body": "hola",
            "MessageSid": "SM456",
        },
        headers={"X-Twilio-Signature": "firma-invalida"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "invalid twilio signature"}
    assert called is False
