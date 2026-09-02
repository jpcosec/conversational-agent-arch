from .identity import Base, UserTraits, Users
from .turns import Turns, TurnKind  # noqa: F401  (registra la tabla turns en Base.metadata)
from .conversation import Conversation, ConversationStatus  # noqa: F401  (registra conversations)

__all__ = [
    "Base",
    "Users",
    "UserTraits",
    "Turns",
    "TurnKind",
    "Conversation",
    "ConversationStatus",
]
