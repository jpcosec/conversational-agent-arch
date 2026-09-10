"""normalize_sender: remitente del proveedor -> (external_id con canal, canal)."""
import pytest

from kb_agent.inbound import canonical_phone, normalize_sender
from kb_agent.orchestrator import channel_from_external_id


@pytest.mark.parametrize("raw, expected", [
    ("whatsapp:+56912345678", ("whatsapp:+56912345678", "whatsapp")),
    ("whatsapp:+56 9 1234 5678", ("whatsapp:+56912345678", "whatsapp")),
    ("WhatsApp:+1", ("whatsapp:+1", "whatsapp")),
    ("+56912345678", ("sms:+56912345678", "sms")),          # SMS pelado de Twilio
    ("  +56 9 1234-5678 ", ("sms:+56912345678", "sms")),
    ("messenger:1234567890", ("messenger:+1234567890", "messenger")),
    ("ui:abc-123", ("ui:abc-123", "ui")),
    ("ui:devsession-1", ("ui:devsession-1", "ui")),   # no es telefono: no se toca
])
def test_normalize_sender(raw, expected):
    assert normalize_sender(raw) == expected


def test_normalized_external_id_is_recognized_by_orchestrator():
    """Lo que sale de normalize_sender nunca cae en canal 'unknown'."""
    for raw in ["+56912345678", "whatsapp:+56912345678"]:
        external_id, channel = normalize_sender(raw)
        assert channel_from_external_id(external_id) == channel


def test_canonical_phone():
    assert canonical_phone("+56 9 1234 5678") == "+56912345678"
    assert canonical_phone("56912345678") == "+56912345678"
    assert canonical_phone("abc") is None
    assert canonical_phone("") is None
    # Un id con algun digito NO es un telefono: antes daba "+1" y unificaba
    # sesiones de UI distintas como la misma persona con identity_key='phone'.
    assert canonical_phone("devsession-1") is None
    assert canonical_phone("123") is None


def test_orchestrator_does_not_unify_ui_sessions_by_stray_digits():
    from kb_agent.orchestrator import Orchestrator
    assert Orchestrator._canonical_phone("ui:devsession-1") is None
    assert Orchestrator._canonical_phone("ui:abc7") is None
    assert Orchestrator._canonical_phone("whatsapp:+56 9 1234 5678") == "+56912345678"
