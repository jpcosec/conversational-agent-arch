"""Chequeo NO bloqueante de la revision de alembic de una base sqlite.

``Base.metadata.create_all()`` (usado por ``Orchestrator`` al arrancar, ver
``kb_agent/orchestrator.py``) crea las tablas que faltan pero NUNCA altera
una tabla existente. Consecuencia real: una base vieja (creada antes de que
un modelo ganara una columna) no explota al arrancar -- explota en el
primer INSERT/SELECT que toque esa columna, con un
``sqlalchemy.exc.OperationalError: no such column: ...`` opaco.

Este modulo compara la ``alembic_version`` de la base contra el HEAD de
``alembic/versions`` y devuelve un diagnostico legible. Se llama desde
``kb_agent/cli.py`` al arrancar; el resultado se imprime como WARNING y
NUNCA debe frenar el arranque (por eso todo esta atrapado en
``check_db_revision`` -- ni una base inexistente, ni alembic mal
configurado, deberian poder crashear la app por este chequeo).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import create_engine

REPO_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = REPO_ROOT / "alembic.ini"


@dataclass(slots=True)
class DbRevisionStatus:
    """Resultado del chequeo. ``ok=True`` solo si la base esta exactamente en HEAD."""

    ok: bool
    message: str
    current_revisions: tuple[str, ...]
    head_revisions: tuple[str, ...]
    #: Cantidad de revisiones entre la base y HEAD. None si no se pudo
    #: calcular (p.ej. la base no tiene alembic_version, o hubo un error).
    revisions_behind: int | None


def check_db_revision(db_url: str) -> DbRevisionStatus:
    """Compara la revision de ``db_url`` contra HEAD de ``alembic/versions``.

    Nunca lanza: cualquier fallo (base inexistente, driver no disponible,
    alembic.ini no encontrado, etc.) se atrapa y vuelve como
    ``DbRevisionStatus(ok=False, ...)`` con el motivo en ``message``.
    """
    try:
        from alembic.config import Config
        from alembic.runtime.migration import MigrationContext
        from alembic.script import ScriptDirectory

        cfg = Config(str(ALEMBIC_INI))
        script = ScriptDirectory.from_config(cfg)
        head_revisions = tuple(script.get_heads())

        engine = create_engine(db_url, future=True)
        try:
            with engine.connect() as conn:
                migration_ctx = MigrationContext.configure(conn)
                current_revisions = tuple(migration_ctx.get_current_heads())
        finally:
            engine.dispose()
    except Exception as exc:  # pragma: no cover - defensivo, no debe crashear la app
        return DbRevisionStatus(
            ok=False,
            message=f"[db_check] no se pudo verificar la revision de la base ({db_url}): {exc!r}",
            current_revisions=(),
            head_revisions=(),
            revisions_behind=None,
        )

    if not current_revisions:
        return DbRevisionStatus(
            ok=False,
            message=(
                f"[db_check] '{db_url}' no tiene tabla alembic_version (esquema sin "
                "versionar por alembic). Si la base ya tiene las tablas al dia (creadas "
                "por create_all()), corre `alembic stamp head`. Si es una base nueva, "
                "corre `alembic upgrade head`."
            ),
            current_revisions=(),
            head_revisions=head_revisions,
            revisions_behind=None,
        )

    if set(current_revisions) == set(head_revisions):
        head_txt = ", ".join(head_revisions) or "(sin migraciones)"
        return DbRevisionStatus(
            ok=True,
            message=f"[db_check] base al dia (revision {head_txt}).",
            current_revisions=current_revisions,
            head_revisions=head_revisions,
            revisions_behind=0,
        )

    revisions_behind: int | None
    try:
        revisions_behind = len(
            list(script.iterate_revisions(head_revisions, current_revisions))
        )
    except Exception:  # pragma: no cover - conteo es best-effort
        revisions_behind = None

    behind_txt = f"{revisions_behind} revision(es)" if revisions_behind is not None else "una o mas revisiones"
    return DbRevisionStatus(
        ok=False,
        message=(
            f"[db_check] la base esta {behind_txt} atras de head "
            f"(actual={current_revisions or '(ninguna)'}, head={head_revisions}). "
            "Corre `alembic upgrade head` -- si no, podes toparte con columnas o "
            "tablas faltantes en pleno uso (create_all() no altera tablas existentes)."
        ),
        current_revisions=current_revisions,
        head_revisions=head_revisions,
        revisions_behind=revisions_behind,
    )
