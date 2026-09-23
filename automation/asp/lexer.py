"""Lexer: extract text tokens from game grid and classify them."""

from __future__ import annotations

from enum import Enum, auto

from automation.asp.ast_nodes import TokenType


class TokenCategory(Enum):
    NOUN = auto()
    OPERATOR = auto()
    PROPERTY = auto()
    MODIFIER = auto()
    UNKNOWN = auto()


NOUNS = frozenset({
    "baba", "wall", "rock", "flag", "skull", "grass",
    "flower", "brick", "jelly", "star", "key", "door",
    "bolt", "leaf", "hand", "ogre", "fence", "water",
    "lava", "robot", "melt", "hot", "weak",
})

OPERATORS = frozenset({"is", "has", "make"})

PROPERTIES = frozenset({
    "you", "win", "stop", "push", "defeat", "sink",
    "melt", "hot", "weak", "move", "shut", "open",
})

MODIFIERS = frozenset({"not", "and", "on", "near", "facing"})


def classify_token(raw: str) -> TokenCategory:
    """Classify a raw token string into a category."""
    t = raw.lower()
    if t in NOUNS:
        return TokenCategory.NOUN
    if t in OPERATORS:
        return TokenCategory.OPERATOR
    if t in PROPERTIES:
        return TokenCategory.PROPERTY
    if t in MODIFIERS:
        return TokenCategory.MODIFIER
    return TokenCategory.UNKNOWN


def strip_text_prefix(cell: str) -> str | None:
    """Extract the meaningful part from a 'text_xxx' cell, or None."""
    if not cell or not cell.startswith("text_"):
        return None
    return cell.removeprefix("text_")


def extract_text_tokens(
    grid: list[list[str]],
) -> list[tuple[int, int, str]]:
    """Return all text block positions and their stripped token strings.

    Coordinates are 1-indexed (game convention).
    """
    tokens: list[tuple[int, int, str]] = []
    for y, row in enumerate(grid):
        for x, cell in enumerate(row):
            for entity in cell.split("<") if cell else []:
                raw = strip_text_prefix(entity)
                if raw is not None:
                    tokens.append((x + 1, y + 1, raw.lower()))
    return tokens


def extract_rules_horizontal(
    grid: list[list[str]],
) -> list[list[tuple[int, int, str]]]:
    """Extract horizontal sequences of consecutive text blocks.

    Returns groups of (x, y, token) tuples that form potential rules.
    """
    sequences: list[list[tuple[int, int, str]]] = []
    current: list[tuple[int, int, str]] = []

    for y, row in enumerate(grid):
        current = []
        for x, cell in enumerate(row):
            has_text = False
            if cell:
                for entity in cell.split("<"):
                    raw = strip_text_prefix(entity)
                    if raw is not None:
                        current.append((x + 1, y + 1, raw.lower()))
                        has_text = True
                        break
            if not has_text:
                if len(current) >= 3:
                    sequences.append(current)
                current = []
        if len(current) >= 3:
            sequences.append(current)

    return sequences


def extract_rules_vertical(
    grid: list[list[str]],
) -> list[list[tuple[int, int, str]]]:
    """Extract vertical sequences of consecutive text blocks."""
    if not grid:
        return []

    height = len(grid)
    width = max(len(row) for row in grid) if grid else 0
    sequences: list[list[tuple[int, int, str]]] = []

    for x in range(width):
        current: list[tuple[int, int, str]] = []
        for y in range(height):
            cell = grid[y][x] if x < len(grid[y]) else ""
            has_text = False
            if cell:
                for entity in cell.split("<"):
                    raw = strip_text_prefix(entity)
                    if raw is not None:
                        current.append((x + 1, y + 1, raw.lower()))
                        has_text = True
                        break
            if not has_text:
                if len(current) >= 3:
                    sequences.append(current)
                current = []
        if len(current) >= 3:
            sequences.append(current)

    return sequences
