"""Handler de la tool ``registrar_enrolamiento`` (KB Antonia — PSP Selfix).

Se registra desde ``project.config.yaml``::

    tools:
      registrar_enrolamiento: kb_agent.tools.enrolamiento:registrar_enrolamiento

PII (decisión deliberada)
--------------------------
Teléfono, correo y nombre son datos personales. Este handler los recibe
solo para completar el paso de enrolamiento -- el alta real en el sistema
del PSP (o la derivación a un doctor) queda fuera de este runtime por
ahora, así que esos valores NO se guardan en ninguna tabla ni se auditan
en claro. El único efecto persistido es marcar ``users.enrolled = True``.

Además, ``execute_tool`` (``kb_agent/tools/__init__.py``) arma el System
Turn que se persiste en ``turns.tool`` con::

    {"tool": name, "status": "ok", "args": args, **result}

``args`` ahí son los argumentos CRUDOS con los que el modelo llamó a la
tool (incluye teléfono/mail/nombre en claro) y NO pasan por
``kb_agent.pii.scrubber`` (ese scrubber solo cubre ``chat_history.content``).
Como el dict-literal aplica ``**result`` después de la clave ``"args"``
puesta con los crudos, si este handler devuelve su propia clave ``"args"``
esa pisa a la original. Por eso el resultado de abajo incluye un ``"args"``
propio con solo booleanos de "vino informado" -- nunca el valor -- para que
teléfono/mail/nombre no terminen en claro en el rastro de auditoría por
turno. No se tocó ``kb_agent/tools/__init__.py`` ni el orquestador (fuera
del alcance de esta tarea); esto es una mitigación acotada al handler.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from kb_agent.models_sql.identity import Users


def registrar_enrolamiento(session: Session, user_id: int | None, args: dict[str, Any]) -> dict[str, Any]:
    telefono = args.get("telefono")
    mail = args.get("mail")
    nombre = args.get("nombre")

    user = session.get(Users, user_id) if user_id is not None else None
    if user is not None:
        user.enrolled = True
        session.commit()

    return {
        "user_id": user_id,
        "enrolled": user is not None,
        # Redactado a propósito -- ver docstring del módulo. Solo se registra
        # si cada dato vino informado, nunca su valor.
        "args": {
            "telefono_provisto": bool(telefono),
            "mail_provisto": bool(mail),
            "nombre_provisto": bool(nombre),
        },
    }
