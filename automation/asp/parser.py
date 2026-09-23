"""Grid text → rule AST via pyparsing."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TypeAlias

import pyparsing as pp

from automation.asp.ast_nodes import (
    OperatorNode,
    RuleNode,
    SubjectNode,
    TargetNode,
)

TokenSeq: TypeAlias = list[tuple[int, int, str]]
Grid: TypeAlias = list[list[str]]

pp.ParserElement.set_default_whitespace_chars(" \t")

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

MIN_RULE_WORDS = 3


def keyword_alternatives(words: frozenset[str]) -> pp.ParserElement:
    return pp.one_of(sorted(words), as_keyword=True, caseless=True)


def target_from_noun(
    source: str,
    location: int,
    tokens: pp.ParseResults,
) -> TargetNode:
    return TargetNode(value=tokens[0], is_property=False)


def target_from_property(
    source: str,
    location: int,
    tokens: pp.ParseResults,
) -> TargetNode:
    return TargetNode(value=tokens[0], is_property=True)


def rule_from_match(
    source: str,
    location: int,
    tokens: pp.ParseResults,
) -> RuleNode:
    match = tokens[0]
    return RuleNode(
        subject=SubjectNode(noun=match.subject),
        operator=OperatorNode(op=match.operator),
        target=match.target,
    )


def build_rule_parser() -> pp.ParserElement:
    """Fresh parser instances so subject/target noun actions do not collide."""
    subject = keyword_alternatives(NOUNS)
    operator = keyword_alternatives(OPERATORS)
    # Nouns before properties so melt / hot / weak count as noun targets.
    target = (
        keyword_alternatives(NOUNS).set_parse_action(target_from_noun)
        | keyword_alternatives(PROPERTIES).set_parse_action(target_from_property)
    )
    return pp.Group(
        subject("subject") + operator("operator") + target("target")
    ).set_parse_action(rule_from_match)


RULE = build_rule_parser()


def rules_in_text(text: str) -> list[RuleNode]:
    return [match[0] for match in RULE.search_string(text)]


def parse_rules(sequences: list[TokenSeq]) -> list[RuleNode]:
    """Parse token sequences into RuleNodes (SUBJECT OPERATOR TARGET)."""
    rules: list[RuleNode] = []
    for seq in sequences:
        if len(seq) < MIN_RULE_WORDS:
            continue
        words = " ".join(token for _, _, token in seq)
        rules.extend(rules_in_text(words))
    return rules


def text_token_from_entity(entity: str) -> str | None:
    if not entity.startswith("text_"):
        return None
    return entity.removeprefix("text_").lower()


def text_on_cell(cell: str) -> str | None:
    if not cell:
        return None
    for entity in cell.split("<"):
        token = text_token_from_entity(entity)
        if token is not None:
            return token
    return None


def flush_run(
    run: TokenSeq,
    min_words: int,
    into: list[TokenSeq],
) -> TokenSeq:
    if len(run) >= min_words:
        into.append(run)
    return []


def runs_along(
    cells: Iterator[tuple[int, int, str | None]],
    min_words: int = MIN_RULE_WORDS,
) -> list[TokenSeq]:
    sequences: list[TokenSeq] = []
    run: TokenSeq = []
    for x, y, token in cells:
        if token is None:
            run = flush_run(run, min_words, sequences)
        else:
            run.append((x, y, token))
    flush_run(run, min_words, sequences)
    return sequences


def horizontal_cells(grid: Grid) -> Iterator[tuple[int, int, str | None]]:
    for y, row in enumerate(grid):
        for x, cell in enumerate(row):
            yield x + 1, y + 1, text_on_cell(cell)


def vertical_cells(grid: Grid) -> Iterator[tuple[int, int, str | None]]:
    if not grid:
        return
    height = len(grid)
    width = max(len(row) for row in grid)
    for x in range(width):
        for y in range(height):
            cell = grid[y][x] if x < len(grid[y]) else ""
            yield x + 1, y + 1, text_on_cell(cell)


def rule_sequences_from_grid(grid: Grid) -> list[TokenSeq]:
    return runs_along(horizontal_cells(grid)) + runs_along(vertical_cells(grid))


def parse_grid(grid: Grid) -> list[RuleNode]:
    """Extract horizontal and vertical text runs from a grid and parse rules."""
    return parse_rules(rule_sequences_from_grid(grid))
