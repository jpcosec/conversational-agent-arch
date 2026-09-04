from .identity import Base, UserTraits, Users
from .turns import Turns, TurnKind  # noqa: F401  (registra la tabla turns en Base.metadata)
from .conversation import Conversation, ConversationStatus  # noqa: F401  (registra conversations)
from .inbound import InboundMessage, InboundStatus  # noqa: F401  (registra inbound_messages)
from .leads import Leads, Visitas, VisitaEstado  # noqa: F401  (registra leads y visitas)

__all__ = [
    "Base",
    "Users",
    "UserTraits",
    "Turns",
    "TurnKind",
    "Conversation",
    "ConversationStatus",
    "InboundMessage",
    "InboundStatus",
    "Leads",
    "Visitas",
    "VisitaEstado",
]
