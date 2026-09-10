from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session


from kb_agent.models_sql.identity import Base, Users
from kb_agent.models_sql.session import ChatHistory
from kb_agent.pii.scrubber import scrub, scrub_unscrubbed_chat_history


def _build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_scrub_masks_phone_email_and_name() -> None:
    text = "Hola, soy Juan Pérez. Llámame al +56 9 1234 5678 o escríbeme a juan.perez@example.com"

    masked = scrub(text)

    assert "+56 9 1234 5678" not in masked
    assert "juan.perez@example.com" not in masked
    assert "Juan Pérez" not in masked
    assert "<PHONE_1>" in masked
    assert "<EMAIL_1>" in masked
    assert "<NAME_1>" in masked


def test_scrub_is_idempotent() -> None:
    text = (
        "Mi RUT es 12.345.678-5, vivo en Avenida Siempre Viva 742 y mi tarjeta "
        "es 4111 1111 1111 1111."
    )

    once = scrub(text)
    twice = scrub(once)

    assert once == twice



def test_worker_rewrites_pending_history_and_marks_rows_scrubbed() -> None:
    with _build_session() as session:
        user = Users(external_id="user-pii", channel="web")
        session.add(user)
        session.flush()

        row = ChatHistory(
            user_id=user.id,
            role="user",
            content="Mi correo es ana@example.com y mi teléfono es +56 9 8765 4321",
        )
        session.add(row)
        session.commit()

        processed = scrub_unscrubbed_chat_history(session)

        assert processed == 1

        persisted = session.scalar(select(ChatHistory).where(ChatHistory.id == row.id))
        assert persisted is not None
        assert persisted.pii_scrubbed is True
        assert "ana@example.com" not in persisted.content
        assert "+56 9 8765 4321" not in persisted.content
        assert "<EMAIL_1>" in persisted.content
        assert "<PHONE_1>" in persisted.content


def test_scrub_keeps_sentence_starters_and_allowlisted_terms() -> None:
    """El patron de NAME tomaba "Hola Carla" y "Soy Antonia" como nombre propio y el
    historial que ve el modelo quedaba como "<NAME_1>, tu asistente del <NAME_2>".
    Las palabras que abren la oracion no son nombre; la marca y el nombre del
    asistente los declara el negocio (``pii_allowlist``) y no se tocan."""
    allow = ["Antonia", "Selfix", "Programa Selfix"]
    assert scrub("Hola Antonia", allowlist=allow) == "Hola Antonia"
    assert scrub("¡Hola! Soy Antonia, tu asistente del Programa Selfix.", allowlist=allow) == (
        "¡Hola! Soy Antonia, tu asistente del Programa Selfix."
    )
    # un nombre real despues de la palabra de arranque si se enmascara
    assert scrub("Hola Carla Rojas, ¿cómo estás?", allowlist=allow) == "Hola <NAME_1>, ¿cómo estás?"
    assert scrub("Me llamo Carla Rojas", allowlist=allow) == "Me llamo <NAME_1>"
    # sin allowlist, la marca sigue protegida solo si abre la oracion
    assert scrub("Soy Antonia") == "Soy Antonia"
    assert "<NAME_1>" in scrub("Contacto: Pedro Soto")
