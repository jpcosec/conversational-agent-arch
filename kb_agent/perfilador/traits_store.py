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

from typing import Any, Sequence

from sqlalchemy.orm import Session

from kb_agent.models_sql.identity import UserTraits

#: Rasgo inferido por el perfilador (LLM) desde el turno.
SOURCE_PROFILER = "perfilador"
#: Rasgo declarado por la persona en el formulario/registro.
SOURCE_FORM = "form"

#: Autoridad relativa de cada fuente. Mayor gana en caso de conflicto de
#: ``source``. Una fuente desconocida se trata como la mas baja.
_SOURCE_RANK = {SOURCE_PROFILER: 0, SOURCE_FORM: 1}

#: Prefijo de los tags que describen a QUE PERFIL corresponde algo. Mismo
#: concepto que ``ContextCompiler._SEGMENT_TAG_PREFIX``.
_SEGMENT_TAG_PREFIX = "user:"


def _segment_tags(doc: dict[str, Any] | None) -> set[str]:
    if not doc:
        return set()
    return {
        tag for tag in (doc.get("tags") or [])
        if isinstance(tag, str) and tag.startswith(_SEGMENT_TAG_PREFIX)
    }


def segmentation_siblings(knowledge: Any, trait_id: str) -> list[str]:
    """Traits que ocupan la MISMA dimension de segmentacion que ``trait_id``.

    Una dimension es un namespace de tags ``user:<dim>.<valor>`` que ademas se
    usa para segmentar contenido, es decir que aparece en documentos que NO son
    traits (``user:specialty.psiquiatria`` esta en las fichas de producto;
    ``user:traits.preferencia_contacto`` no esta en ninguna). Dos valores de
    una misma dimension son excluyentes: un medico ejerce UNA especialidad, y
    el compilador filtra su catalogo por ese tag.

    Sin esto el arbitraje era por ``trait_id``, no por dimension: medido en la
    auditoria del 2026-09-09, a un psiquiatra declarado por formulario el
    perfilador le agrego traumatologia y el turno siguiente llevo las dos
    especialidades al prompt.

    Fail-open: si la KB no responde, devuelve ``[]`` (comportamiento previo).
    """
    try:
        traits = list(knowledge.docs_by_type("trait"))
        propio = _segment_tags(next((t for t in traits if t.get("id") == trait_id), None))
        if not propio:
            return []
        namespaces = {tag.rsplit(".", 1)[0] for tag in propio if "." in tag}
        if not namespaces:
            return []
        # Solo son dimensiones los namespaces que segmentan contenido.
        trait_ids = {t.get("id") for t in traits}
        segmentadores = {
            tag.rsplit(".", 1)[0]
            for doc in knowledge.docs_by_type("domain")
            if doc.get("id") not in trait_ids
            for tag in _segment_tags(doc) if "." in tag
        }
        dimensiones = namespaces & segmentadores
        if not dimensiones:
            return []
        return sorted(
            str(t.get("id"))
            for t in traits
            if t.get("id") and t.get("id") != trait_id
            and any(tag.rsplit(".", 1)[0] in dimensiones for tag in _segment_tags(t) if "." in tag)
        )
    except Exception:
        return []


def upsert_user_trait(
    session: Session,
    *,
    user_id: int,
    trait_id: str,
    confidence: float,
    source: str,
    exclusive_with: Sequence[str] = (),
) -> None:
    """Inserta o actualiza un ``user_traits`` respetando la precedencia de fuente.

    * confidence: siempre queda el maximo observado.
    * source: gana la fuente de mayor autoridad (``form`` > ``perfilador``);
      en empate se mantiene la ya persistida.
    * ``exclusive_with``: ids que ocupan la MISMA dimension (ver
      ``segmentation_siblings``). Si el usuario ya tiene uno de esos traits
      escrito por una fuente de MAYOR autoridad, el nuevo no se escribe -- lo
      declarado en el formulario no lo pisa una inferencia del LLM. Si la
      fuente nueva manda, los de la dimension se borran: un valor por
      dimension, nunca dos.
    """
    if exclusive_with:
        rivales = (
            session.query(UserTraits)
            .filter(UserTraits.user_id == user_id, UserTraits.trait_id.in_(list(exclusive_with)))
            .all()
        )
        rank_nuevo = _SOURCE_RANK.get(source, -1)
        if any(_SOURCE_RANK.get(r.source, -1) > rank_nuevo for r in rivales):
            return  # la dimension ya la ocupa una fuente mas autoritativa
        for rival in rivales:
            session.delete(rival)

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
