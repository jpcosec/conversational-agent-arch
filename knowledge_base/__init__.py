"""knowledge CLI — bridge semántico entre SLDB + KGDB + SQL para agentes conversacionales.

Uso:
    python -m knowledge_base --kb <path> explore <consulta>
    python -m knowledge_base --kb <path> show <atom_id>
    python -m knowledge_base --kb <path> step next --user <id>
    python -m knowledge_base --kb <path> traits --user <id>
    python -m knowledge_base --kb <path> self
    python -m knowledge_base --kb <path> context --user <id>
    python -m knowledge_base --kb <path> propose --model <m> --body <yaml>
"""

from knowledge_base.cli import main
from knowledge_base.operations import KnowledgeOperations

__all__ = ["main", "KnowledgeOperations"]