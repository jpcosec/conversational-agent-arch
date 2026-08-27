"""Siembra la DB de perfilado con usuarios demo (Antonia / PSP Selfix).

Crea usuarios con historial de chat + traits que cruzan con las fichas SLDB
(trait-antonia-*), para que la vista /users muestre perfiles, eventos y
conversaciones poblados.

Uso:
    python -m kb_agent.seed_demo_users            # usa PROFILING_DB del config
    python -m kb_agent.seed_demo_users --db ruta.sqlite

Idempotente: hace upsert por external_id (borra y recrea el usuario demo).
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from kb_agent.models_sql.identity import Base as IdentityBase, Users, UserTraits
from kb_agent.models_sql.session import ChatHistory
from kb_agent.project_config import load_project_config

# trait_ids reales de la KB de Antonia (cruzan con fichas SLDB type.knowledge.trait)
TRAITS = {
    "primera_vez": "trait-antonia-primera-vez",
    "ansioso": "trait-antonia-ansioso-aplicacion",
    "adherencia": "trait-antonia-buena-adherencia",
    "dudas": "trait-antonia-dudas-efectos",
    "recordatorios": "trait-antonia-prefiere-recordatorios",
}

# Usuarios demo: perfiles distintos del PSP Selfix
DEMO_USERS = [
    {
        "external_id": "wa-56991112233",
        "channel": "whatsapp",
        "traits": [
            (TRAITS["primera_vez"], 0.92, "reflector"),
            (TRAITS["ansioso"], 0.85, "reflector"),
            (TRAITS["dudas"], 0.71, "perfilador"),
        ],
        "chats": [
            ("user", "hola, me acaban de recetar Selfix y nunca me he inyectado nada"),
            ("assistant", "Hola, tranquila. Te acompaño en tu primera aplicación paso a paso."),
            ("user", "me da miedo la aguja, es muy grande?"),
            ("assistant", "La aguja es muy fina y corta. Muchas personas no sienten casi nada."),
            ("user", "y si me equivoco en la dosis?"),
            ("assistant", "El dispositivo tiene tope de dosis, es difícil equivocarse. Te muestro el video aprobado."),
        ],
    },
    {
        "external_id": "wa-56944455566",
        "channel": "whatsapp",
        "traits": [
            (TRAITS["adherencia"], 0.96, "reflector"),
            (TRAITS["recordatorios"], 0.88, "perfilador"),
        ],
        "chats": [
            ("user", "quiero activar los recordatorios semanales"),
            ("assistant", "Perfecto. ¿Qué día y hora prefieres para tu aplicación?"),
            ("user", "los domingos a las 9am"),
            ("assistant", "Listo, te recordaré cada domingo 9am. Vas muy bien con tu adherencia."),
            ("user", "gracias, no he fallado ninguna semana"),
            ("assistant", "Excelente constancia. Eso es clave para el tratamiento."),
        ],
    },
    {
        "external_id": "web-anon-4821",
        "channel": "web",
        "traits": [
            (TRAITS["dudas"], 0.79, "perfilador"),
            (TRAITS["ansioso"], 0.64, "perfilador"),
        ],
        "chats": [
            ("user", "es normal sentir dolor en el sitio de inyección?"),
            ("assistant", "Un leve enrojecimiento o molestia es común y transitorio. Te explico la rotación de sitios."),
            ("user", "cuánto dura ese efecto?"),
            ("assistant", "Normalmente unas horas. Si persiste más de 2 días, conviene consultar."),
        ],
    },
    {
        "external_id": "wa-56977788899",
        "channel": "whatsapp",
        "traits": [
            (TRAITS["primera_vez"], 0.68, "perfilador"),
            (TRAITS["recordatorios"], 0.72, "perfilador"),
            (TRAITS["adherencia"], 0.55, "reflector"),
        ],
        "chats": [
            ("user", "cómo conservo el producto?"),
            ("assistant", "En refrigeración entre 2 y 8°C, sin congelar. Te explico el detalle."),
            ("user", "y si viajo?"),
            ("assistant", "Usa una nevera portátil con gel refrigerante. No lo expongas al calor."),
        ],
    },
]


def seed(db_path: str) -> dict:
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    IdentityBase.metadata.create_all(engine)
    ChatHistory.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, future=True)

    now = datetime.now(timezone.utc)
    created = {"users": 0, "traits": 0, "chats": 0}

    with Session() as s:
        for i, spec in enumerate(DEMO_USERS):
            # upsert: borra usuario demo previo (cascade borra traits)
            existing = s.query(Users).filter(Users.external_id == spec["external_id"]).first()
            if existing:
                s.query(ChatHistory).filter(ChatHistory.user_id == existing.id).delete()
                s.delete(existing)
                s.flush()

            u = Users(
                external_id=spec["external_id"],
                channel=spec["channel"],
                created_at=now - timedelta(days=7 - i),
            )
            s.add(u)
            s.flush()  # obtener u.id
            created["users"] += 1

            # traits
            for trait_id, conf, source in spec["traits"]:
                s.add(UserTraits(
                    user_id=u.id,
                    trait_id=trait_id,
                    confidence=conf,
                    source=source,
                    created_at=now - timedelta(days=5 - i, hours=2),
                ))
                created["traits"] += 1

            # historial de chat (timestamps incrementales)
            base = now - timedelta(days=5 - i)
            for j, (role, content) in enumerate(spec["chats"]):
                s.add(ChatHistory(
                    user_id=u.id,
                    role=role,
                    content=content,
                    pii_scrubbed=(role == "user"),
                    created_at=base + timedelta(minutes=j * 3),
                ))
                created["chats"] += 1

        s.commit()

    engine.dispose()
    return created


def main() -> None:
    ap = argparse.ArgumentParser(description="Siembra usuarios demo en la DB de perfilado")
    ap.add_argument("--db", default=None, help="ruta al sqlite de perfilado (default: config)")
    args = ap.parse_args()

    db_path = args.db
    if db_path is None:
        cfg = load_project_config()
        db_path = str(cfg.profiling_db)

    result = seed(db_path)
    print(f"Sembrado en {db_path}:")
    print(f"  usuarios: {result['users']}")
    print(f"  traits:   {result['traits']}")
    print(f"  chats:    {result['chats']}")


if __name__ == "__main__":
    main()
