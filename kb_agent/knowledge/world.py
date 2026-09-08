"""La KB de un negocio abierta como mundo de pron: un ``World`` por proceso.

Todo el acceso del runtime al store (documentos) y al grafo (aristas tipadas
de kgdb) pasa por aca. Lo unico propio de este modulo es la politica de
arranque: un store que nunca paso por ``kgdb init`` se inicializa (modelos
``RelationTypeDoc``/``RelationDoc``, tipos builtin, predicados) y el grafo
derivado (``<kb>/.pron/graph.nx.json``) se reconstruye solo cuando los
hashes de los modelos cambiaron (``World.refresh_if_stale``).
"""
from __future__ import annotations

import logging
from pathlib import Path

from kgdb.world import init_world
from pron.world import World

logger = logging.getLogger(__name__)


def open_world(kb_root: str | Path, pythonpath: str | Path | None = None, *, refresh: bool = True) -> World:
    """Abre la KB en ``kb_root`` (el directorio que contiene ``.sldb/``).

    ``pythonpath`` es la raiz donde viven los modelos (``kb_agent.models``),
    por defecto el padre de ``kb_root``. Con ``refresh`` (default) deja el
    grafo tipado fresco: corre ``kgdb init`` si el store no lo tuvo y
    reconstruye el grafo si los modelos cambiaron desde la ultima vez.
    """
    root = Path(kb_root).resolve()
    pp = str(pythonpath) if pythonpath is not None else str(root.parent)
    world = World(root, pythonpath=pp)
    if refresh:
        refresh_world(world)
    return world


def refresh_world(world: World) -> bool:
    """``kgdb init`` si falta y ``refresh_if_stale``. Devuelve si reconstruyo el grafo."""
    if "RelationTypeDoc" not in world.model_names():
        report = init_world(world.store.sp, world.store.pythonpath)
        logger.info("kgdb init en %s: %s", world.root, report.summary())
        world.store.invalidate()
    return world.refresh_if_stale()
