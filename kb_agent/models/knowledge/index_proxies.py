"""Campos de indexación compartidos por todos los modelos de la KB.

Estos campos son PROXIES DE INDEXACIÓN: permiten al Compilador decidir
relevancia sin leer el body del atom. Se calculan OFFLINE (plano de
fortalecimiento) por el pipeline `knowledge index *`, nunca por un agente
conversacional en runtime.

Todos son opcionales: un atom sin indexar sigue siendo válido; el pipeline
offline los rellena después.
"""
from __future__ import annotations

from pydantic import Field

from sldb import StructuredNLDoc

# Bloque de template reutilizable: marcadores de frontmatter para los proxies.
# Se inserta en el frontmatter de cada modelo, antes del cierre `---`.
INDEX_PROXY_TEMPLATE = """summary: ⸢optrev•summary⸥
embedding: ⸢optrev•embedding⸥
parent: ⸢optrev•parent⸥
semantic_anchors: ⸢optrev•semantic_anchors⸥"""


class IndexProxies(StructuredNLDoc):
    """Mixin con los proxies de indexación calculados offline.

    Hereda de StructuredNLDoc para que los modelos concretos puedan
    heredar de esta clase directamente y obtener los campos.
    """

    summary: str | None = Field(
        default=None,
        description=(
            "Resumen textual corto (proxy). Permite al Compilador evaluar "
            "relevancia sin leer el body. Calculado offline por 'knowledge index proxies'."
        ),
    )
    embedding: list[float] | None = Field(
        default=None,
        description=(
            "Vector de embedding precalculado offline. Se compara contra el "
            "embedding in-situ de la query. Escrito por 'knowledge index embeddings'."
        ),
    )
    parent: str | None = Field(
        default=None,
        description=(
            "Tag padre en la jerarquía enciclopédica (ej. 'domain:catalogo'). "
            "Define posición en el árbol. Escrito por 'knowledge index hierarchy'."
        ),
    )
    semantic_anchors: list[str] | None = Field(
        default=None,
        description=(
            "Palabras/frases ancla para match rápido (fuzzy/keyword). "
            "Calculadas offline por 'knowledge index proxies'."
        ),
    )