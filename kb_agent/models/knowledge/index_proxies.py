"""Campo de indexación compartido por todos los modelos de la KB.

``summary`` es un PROXY DE INDEXACIÓN: permite al Compilador decidir relevancia
sin leer el body del atom, y es el texto que se embebe para la similitud.

Lo que antes vivía acá como campos (``embedding``, ``parent``,
``semantic_anchors``) ya no es parte del documento: los vectores los guarda el
``DocumentIndex`` de pron en un archivo derivado (``<kb>/.pron/``, fuera de
git, keyed por el hash del documento), y la jerarquía de tags la deriva sldb
(``semantic_dag``) y la expone kgdb como aristas ``semantic_parent``.
"""
from __future__ import annotations

from typing import ClassVar

from pydantic import Field
from sldb import StructuredNLDoc

# Bloque de template reutilizable: se inserta en el frontmatter de cada modelo.
INDEX_PROXY_TEMPLATE = """summary: ⸢rev•summary⸥"""


class IndexProxies(StructuredNLDoc):
    """Mixin con el proxy de indexación.

    Hereda de StructuredNLDoc para que los modelos concretos puedan
    heredar de esta clase directamente y obtener los campos.
    """

    # Familia semántica raíz que este modelo ocupa en el árbol de tags.
    # Uno de: "self" | "conversation" | "domain" | "user".
    # Se declara por clase, no se deriva en runtime.
    __family__: ClassVar[str | None] = None

    @classmethod
    def family(cls) -> str | None:
        """Rama raíz del árbol de tags que este modelo ocupa."""
        return cls.__family__

    summary: str = Field(
        description=(
            "Resumen textual corto (proxy). OBLIGATORIO. Permite al Compilador "
            "evaluar relevancia sin leer el body y es el texto que se embebe. "
            "Lo escribe el creador del atom (humano o Reflector)."
        ),
    )
