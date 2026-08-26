"""Argument parser for the knowledge CLI."""
from __future__ import annotations

import argparse


EPILOG = """
Commands:
  explore                Entry points: tags raíz del grafo KGDB
  explore --tag <t>      Expande un tag: padre + hijos + docs
  explore --atom <id>    Vecindario de un doc: tags + hermanos
  show <atom_id>         Muestra un atom completo por su id
  step next --user <id>  Siguiente paso conversacional desde sesión + KGDB
  traits --user <id>     Traits del usuario resueltos contra SLDB
  self                   Identidad + estilo + límites del agente
  context --user <id>    Estado completo de la sesión (todo-en-uno)
  propose --model <m>    Propuesta de atom (para el Reflector)
         --body <yaml>

Offline (fortalecimiento de la KB):
  index embeddings       Calcula embeddings para DomainAtom y RuleAtom
  index hierarchy        Construye jerarquía enciclopédica en semantic DAG
  promote <atom_id>      Promueve un atom propuesto a activo
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="knowledge",
        description="knowledge: base de conocimiento semántica para agentes conversacionales.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=EPILOG,
    )
    parser.add_argument("--kb", default=".", help="Ruta al root de la KB (default: .)")
    parser.add_argument("--db", default=None, help="URL de la base de datos SQL (default: <kb>/.knowledge.db)")
    parser.add_argument("--pythonpath", default=None, help="Python path para resolución de modelos SLDB (default: parent del kb_root)")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # explore
    p = subparsers.add_parser("explore", help="Navegación del grafo KGDB de la KB")
    p.add_argument("--tag", default=None, help="Expande un tag: padre + hijos + docs")
    p.add_argument("--atom", default=None, help="Vecindario de un doc: tags + hermanos")

    # show
    p = subparsers.add_parser("show", help="Muestra un atom completo")
    p.add_argument("atom_id", help="Id del atom (ej. self-antonia)")

    # step next
    p = subparsers.add_parser("step", help="Navegación del diagrama de conversación")
    s = p.add_subparsers(dest="step_command", required=True)
    pn = s.add_parser("next", help="Siguiente paso válido desde el estado de sesión")
    pn.add_argument("--user", required=True, help="External user id (ej. wa:+56900000000)")

    # traits
    p = subparsers.add_parser("traits", help="Traits del usuario resueltos")
    p.add_argument("--user", required=True, help="External user id")

    # self
    subparsers.add_parser("self", help="Identidad + estilo + límites del agente")

    # context
    p = subparsers.add_parser("context", help="Estado completo de la sesión (todo-en-uno)")
    p.add_argument("--user", required=True, help="External user id")

    # propose
    p = subparsers.add_parser("propose", help="Propuesta de atom (para el Reflector)")
    p.add_argument("--model", required=True, help=f"Modelo del atom: {', '.join(['domain','rule','tool','trait','step','self','style','boundary','strategy','fallback'])}")
    p.add_argument("--body", required=True, help="Contenido del atom en YAML/JSON")

    # add index subcommands
    _add_index_commands(subparsers)

    return parser


def _add_index_commands(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("index", help="Pipeline offline de fortalecimiento de la KB")
    s = p.add_subparsers(dest="index_command", required=True)

    pe = s.add_parser("embeddings", help="Calcula embeddings offline para DomainAtom y RuleAtom")
    pe.add_argument("--model", default="jinaai/jina-embeddings-v2-base-es", help="Modelo de embeddings (default: jina-embeddings-v2-base-es)")

    s.add_parser("hierarchy", help="Construye jerarquía enciclopédica en el semantic DAG")

    p = subparsers.add_parser("promote", help="Promueve un atom propuesto a activo")
    p.add_argument("atom_id", help="Id del atom a promover")