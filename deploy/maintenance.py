"""Mantenimiento del sqlite del volumen de Modal (inspeccionar / limpiar / sembrar).

El volumen ``kb-agent-runtime-data`` persiste entre deploys, asi que acumula
datos de despliegues viejos -- incluidos los de cuando el runtime servia la KB
de prueba (Don Peppe) en vez de Antonia. Este modulo permite mirarlo y
limpiarlo sin adivinar desde afuera.

    modal run deploy/maintenance.py::inspect
    modal run deploy/maintenance.py::clean_and_seed

``inspect`` es de solo lectura. ``clean_and_seed`` BORRA las conversaciones y
vuelve a sembrar los usuarios demo de Antonia: no toca el esquema (lo maneja
alembic al arrancar ``serve``).
"""
from __future__ import annotations

import modal

from deploy.modal_app import (
    APP_NAME,
    REMOTE_APP_DIR,
    VOLUME_NAME,
    image,
)

app = modal.App(f"{APP_NAME}-maintenance", image=image)
data_volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

DB_PATH = "/data/ui-chat.sqlite"


def _connect():
    import sqlite3

    return sqlite3.connect(DB_PATH)


@app.function(volumes={"/data": data_volume}, timeout=900)
def inspect() -> None:
    """Muestra que hay en la base del volumen, sin tocar nada."""
    import os

    if not os.path.exists(DB_PATH):
        print(f"{DB_PATH} no existe todavia")
        return

    con = _connect()
    try:
        tablas = sorted(r[0] for r in con.execute(
            "select name from sqlite_master where type='table'"))
        print("tablas:", tablas)
        for t in tablas:
            n = con.execute(f"select count(*) from {t}").fetchone()[0]
            print(f"  {t}: {n}")

        print("\nusuarios:")
        for r in con.execute("select id, external_id, channel from users"):
            print("   ", r)

        print("\nprimeros mensajes por usuario (para ver de que KB son):")
        for uid, ext in con.execute("select id, external_id from users"):
            rows = con.execute(
                "select role, substr(content,1,90) from chat_history "
                "where user_id=? order by id limit 4", (uid,)).fetchall()
            if rows:
                print(f"  -- {ext}")
                for role, txt in rows:
                    print(f"     {role:9} {txt}")
    finally:
        con.close()


@app.function(volumes={"/data": data_volume}, timeout=1800)
def clean_and_seed() -> None:
    """Borra las conversaciones y siembra los usuarios demo de Antonia.

    Borra en orden de dependencia (hijos antes que ``users``). No toca el
    esquema: de eso se encarga alembic al arrancar ``serve``.
    """
    import os
    import sys

    if REMOTE_APP_DIR not in sys.path:
        sys.path.insert(0, REMOTE_APP_DIR)
    os.chdir(REMOTE_APP_DIR)
    os.environ["PROJECT_CONFIG"] = f"{REMOTE_APP_DIR}/project.config.yaml"

    con = _connect()
    try:
        existentes = {r[0] for r in con.execute(
            "select name from sqlite_master where type='table'")}
        # De hijos a padre: turns/chat_history/user_traits/session_state
        # referencian users.
        for t in ("turns", "chat_history", "user_traits", "session_state",
                  "reservas", "recordatorios", "users"):
            if t in existentes:
                n = con.execute(f"select count(*) from {t}").fetchone()[0]
                con.execute(f"delete from {t}")
                print(f"  borradas {n} filas de {t}")
        con.commit()
    finally:
        con.close()

    from kb_agent.seed_demo_users import seed

    stats = seed(DB_PATH)
    print("sembrado:", stats)

    con = _connect()
    try:
        for t in ("users", "user_traits", "chat_history", "turns"):
            try:
                n = con.execute(f"select count(*) from {t}").fetchone()[0]
                print(f"  {t}: {n}")
            except Exception as exc:  # tabla ausente en una base vieja
                print(f"  {t}: {exc}")
    finally:
        con.close()

    data_volume.commit()
    print("volumen commiteado")
