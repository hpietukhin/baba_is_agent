"""Generate Clorm FactBase from game grid + parsed AST rules."""

from __future__ import annotations

from clorm import FactBase

from automation.asp.ast_nodes import RuleNode
from automation.asp.parser import parse_grid
from automation.asp.predicates import AtInit, RuleIs, TextBlock

# Background objects that don't participate in game logic
_BACKGROUND = frozenset({"tile", "grass", "flower", "brick"})


def _collect_objects(
    grid: list[list[str]],
) -> dict[str, list[tuple[int, int]]]:
    """Collect all physical (non-text) objects and their positions.

    Returns dict mapping object_type → list of (x, y) positions (1-indexed).
    """
    objects: dict[str, list[tuple[int, int]]] = {}
    for y, row in enumerate(grid):
        for x, cell in enumerate(row):
            if not cell:
                continue
            for entity in cell.split("<"):
                if not entity.startswith("text_") and entity not in _BACKGROUND:
                    objects.setdefault(entity, []).append((x + 1, y + 1))
    return objects


def _collect_text_blocks(
    grid: list[list[str]],
) -> list[tuple[int, int, str]]:
    """Collect all text block positions and their type strings."""
    blocks: list[tuple[int, int, str]] = []
    for y, row in enumerate(grid):
        for x, cell in enumerate(row):
            if not cell:
                continue
            for entity in cell.split("<"):
                if entity.startswith("text_"):
                    blocks.append((x + 1, y + 1, entity))
    return blocks


def generate_facts(
    grid: list[list[str]],
    custom_rules: list[RuleNode] | None = None,
) -> FactBase:
    """Build a FactBase from the game grid.

    Args:
        grid: 2D array of cell strings (e.g. "baba", "text_is", "wall<rock").
        custom_rules: Optional pre-parsed rules. If None, parsed from grid.

    Returns:
        Clorm FactBase with AtInit, TextBlock, and RuleIs facts.
    """
    fb = FactBase()

    # Physical objects
    obj_id = 0
    objects = _collect_objects(grid)
    for obj_type, positions in sorted(objects.items()):
        for x, y in positions:
            fb.add(AtInit(obj_id=obj_id, obj_type=obj_type, x=x, y=y))
            obj_id += 1

    # Text blocks
    block_id = 0
    text_blocks = _collect_text_blocks(grid)
    for x, y, block_type in text_blocks:
        # Normalize: "text_baba" → "baba" for the block_type field
        normalized = block_type.removeprefix("text_")
        fb.add(TextBlock(block_id=block_id, block_type=normalized, x=x, y=y))
        block_id += 1

    # Rules
    if custom_rules is not None:
        rules = custom_rules
    else:
        rules = parse_grid(grid)

    for rule in rules:
        fb.add(
            RuleIs(subject=rule.subject.noun, target=rule.target.value)
        )

    return fb
