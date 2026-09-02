"""Upsert de ``user_traits`` con politica de precedencia por fuente.

Dos caminos escriben ``user_traits``:

* ``perfilador`` -- rasgos INFERIDos por el LLM desde el turno (confidence < 1).
* ``form`` -- rasgos DECLARADOS por la persona en el registro/formulario
  (confidence == 1.0, sin LLM).

Un dato declarado en el form es mas autoritativo que uno inferido: si la
persona dijo "vivo en Chile" en el registro, el perfilador no debe degradar
ese trait a ``source='perfilador'`` mas tarde. Por eso el upsert es
compartido y aplica una jerarquia de fuentes explicita en vez de pisar el
``source`` siempre (bug previo del perfilador).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from kb_agent.models_sql.identity import UserTraits

#: Rasgo inferido por el perfilador (LLM) desde el turno.
SOURCE_PROFILER = "perfilador"
#: Rasgo declarado por la persona en el formulario/registro.
SOURCE_FORM = "form"

#: Autoridad relativa de cada fuente. Mayor gana en caso de conflicto de
#: ``source``. Una fuente desconocida se trata como la mas baja.
_SOURCE_RANK = {SOURCE_PROFILER: 0, SOURCE_FORM: 1}


def upsert_user_trait(
    session: Session,
    *,
    user_id: int,
    trait_id: str,
    confidence: float,
    source: str,
) -> None:
    """Inserta o actualiza un ``user_traits`` respetando la precedencia de fuente.

    * confidence: siempre queda el maximo observado.
    * source: gana la fuente de mayor autoridad (``form`` > ``perfilador``);
      en empate se mantiene la ya persistida.
    """
    persisted = session.get(UserTraits, {"user_id": user_id, "trait_id": trait_id})
    if persisted is None:
        session.add(
            UserTraits(
                user_id=user_id,
                trait_id=trait_id,
                confidence=confidence,
                source=source,
            )
        )
        return

    persisted.confidence = max(persisted.confidence, confidence)
    if _SOURCE_RANK.get(source, -1) > _SOURCE_RANK.get(persisted.source, -1):
        persisted.source = source
