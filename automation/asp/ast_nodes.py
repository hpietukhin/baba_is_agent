"""AST node definitions for parsed Baba Is You rules."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    NOUN = auto()
    OPERATOR = auto()
    PROPERTY = auto()


@dataclass(frozen=True, slots=True)
class SubjectNode:
    noun: str


@dataclass(frozen=True, slots=True)
class OperatorNode:
    op: str  # "is", "has", "make"


@dataclass(frozen=True, slots=True)
class TargetNode:
    value: str
    is_property: bool = True


@dataclass(frozen=True, slots=True)
class RuleNode:
    subject: SubjectNode
    operator: OperatorNode
    target: TargetNode
