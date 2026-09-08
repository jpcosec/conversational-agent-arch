"""El puerto de embeddings del runtime: un ``Embedder`` de pron sobre fastembed.

pron define el contrato (``pron.embedder.Embedder``: ``id()`` y ``embed(texts)``) y
el indice de documentos (``pron.embedder.DocumentIndex``: vectores en un archivo
derivado fuera de git, keyed por el hash del documento). Lo unico propio de este
repo es QUE modelo se usa para el espanol y donde se cachea su descarga.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Sequence

#: Modelo por defecto: espanol, 768 dimensiones.
DEFAULT_MODEL = "jinaai/jina-embeddings-v2-base-es"


class FastembedEmbedder:
    """``pron.embedder.Embedder`` sobre ``fastembed.TextEmbedding``.

    Cargar el modelo tarda ~1 minuto en frio y pesa ~615 MB; se descarga a
    ``cache_dir`` (``EMBEDDING_CACHE_DIR`` o ``<kb>/.embedding_cache``). En un
    despliegue efimero (Modal) hay que apuntar esa variable a un volumen
    persistente. La carga es perezosa: construir el adaptador no descarga nada.
    """

    def __init__(self, model_name: str = DEFAULT_MODEL, cache_dir: str | Path | None = None) -> None:
        self.model_name = model_name
        self.cache_dir = str(cache_dir) if cache_dir else None
        self._model = None

    def id(self) -> str:
        return f"fastembed:{self.model_name}"

    def _load(self):
        if self._model is None:
            from fastembed import TextEmbedding

            self._model = TextEmbedding(model_name=self.model_name, cache_dir=self.cache_dir)
        return self._model

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [[float(v) for v in vec] for vec in self._load().embed(list(texts))]


def default_embedder(kb_root: Path, model_name: str | None = None) -> FastembedEmbedder:
    cache_dir = os.environ.get("EMBEDDING_CACHE_DIR") or str(Path(kb_root) / ".embedding_cache")
    return FastembedEmbedder(model_name or DEFAULT_MODEL, cache_dir)
