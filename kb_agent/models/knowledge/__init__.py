"""Knowledge base models for kb-agent-runtime.

Each model is a StructuredNLDoc subclass representing a distinct
knowledge type in the KB. Models are registered in their own
.knowledge/ store, separate from deskops models.

Taxonomy:
  domain     → DomainAtom        — factual business knowledge
  rule       → RuleAtom          — conditional behavior heuristics
  tool       → ToolAtom          — JSON-schema tool definitions
  trait      → TraitAtom         — reusable user characteristic descriptors
  step       → ConversationStep  — conversation flow nodes with slots/transitions
  self       → SelfDeclaration   — identity statement (whoami)
  style      → StyleGuide        — tone, register, phrasing, length
  boundary   → CapabilityBoundary — limitations and escalation rules
  strategy   → StrategyRule      — high-level interaction strategy
  fallback   → FallbackRule      — empty-context fallback messages
  gate       → GateCriterion     — post-draft policy checks kept invisible to the current turn compiler
  agent      → AgentFraming      — per-agent business framing injected into agent prompts
"""

from .index_proxies import IndexProxies, INDEX_PROXY_TEMPLATE
from .agent_framing import AgentFraming
from .boundary import CapabilityBoundary
from .domain import DomainAtom, AtomQuestion, AtomTag
from .fallback import FallbackRule
from .gate import GateCriterion
from .rule import RuleAtom
from .self_declaration import SelfDeclaration
from .step import ConversationStep
from .strategy import StrategyRule
from .style import StyleGuide
from .tool import ToolAtom
from .trait import TraitAtom

__all__ = [
    "AgentFraming",
    "AtomQuestion",
    "AtomTag",
    "CapabilityBoundary",
    "ConversationStep",
    "DomainAtom",
    "FallbackRule",
    "GateCriterion",
    "IndexProxies",
    "INDEX_PROXY_TEMPLATE",
    "RuleAtom",
    "SelfDeclaration",
    "StrategyRule",
    "StyleGuide",
    "ToolAtom",
    "TraitAtom",
]