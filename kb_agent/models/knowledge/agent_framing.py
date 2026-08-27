from pydantic import Field

from sldb import StructuredNLDoc
from .index_proxies import IndexProxies, INDEX_PROXY_TEMPLATE

from .domain import AtomTag


class AgentFraming(IndexProxies):
    """Encuadre de negocio de un agente LLM del sistema.

    Los agentes del runtime (Conversador, Ruteador, Orquestador, Gate) tienen
    un prompt con DOS capas:

      - la *doctrina* (mecanica fija del runtime: familias de documentos,
        regla de oro, formato de salida) — vive en el CODIGO (``render_*`` de
        ``kb_agent.agents``), no cambia por negocio.
      - el *encuadre* (quien es este agente EN ESTE negocio: "gate regulatorio
        de un programa de farmacovigilancia", ejemplos del dominio) — vive
        AQUI, en la KB, indexado por ``role`` (uno de ``AgentRole``).

    Doctrina "una KB = un negocio": mover el encuadre a la KB evita hardcodear
    el dominio (clinico, gastronomico, etc.) en el codigo. Un negocio sin un
    ``AgentFraming`` para un rol cae al encuadre generico del ``render_*``.
    """

    __family__ = "agent"
    __semantics__ = {
        "type": ["knowledge", "agent"],
        "workspace": ["knowledge"],
    }
    __template__ = f"""---
id: ⸢rev•id⸥
title: ⸢rev•title⸥
atom_type: agent
role: ⸢rev•role⸥
tags: ⸢rev•tags⸥
provenance: ⸢optrev•provenance⸥
{INDEX_PROXY_TEMPLATE}
---

# ⸢render•title⸥

## Framing

⸢rev•framing⸥

## Examples

⸢optrev•examples⸥
""".strip()

    id: str = Field(
        description="Stable framing identifier, conventionally 'agent-<role>'."
    )
    title: str = Field(
        description="Short title (e.g. 'Encuadre del Gate', 'Encuadre del Ruteador')."
    )
    role: str = Field(
        description=(
            "Agente al que aplica este encuadre. Uno de los valores de "
            "AgentRole: 'conversador' | 'router' | 'orchestrator' | 'gate'."
        ),
    )
    framing: str = Field(
        description=(
            "Encuadre de negocio del agente: quien es EN ESTE negocio y en que "
            "dominio opera. Se inyecta como lead-in del prompt del agente, "
            "delante de la doctrina fija del runtime. Nada de mecanica del "
            "runtime aca (eso vive en el codigo)."
        ),
    )
    examples: str = Field(
        default="",
        description=(
            "Ejemplos concretos del dominio para guiar al agente (opcional). "
            "Ej. para el ruteador: casos de que documentos meter y por que."
        ),
    )
    tags: list[AtomTag] = Field(
        default_factory=list,
        description="Namespaced semantic tags, e.g. agent:gate, agent:router.",
    )
    provenance: str | None = Field(
        default=None,
        description="Optional URL or path to the authoritative source.",
    )
