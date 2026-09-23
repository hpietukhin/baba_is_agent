"""Solve a Baba Is You map with the Clingo encoding in baba.lp."""

from __future__ import annotations

from itertools import count
from pathlib import Path
from typing import NamedTuple

import clingo

DOMAIN_FILE = Path(__file__).with_name("baba.lp")
TURN_PROGRAMS = (
    "step",
    "you",
    "push",
    "stop",
    "melt",
    "tele",
    "defeat",
    "meta",
    "check",
)

LEGEND: dict[str, tuple[str, str | None]] = {
    "#": ("wall", None),
    "B": ("baba", None),
    "R": ("rock", None),
    "F": ("flag", None),
    "b": ("text", "baba"),
    "i": ("text", "is"),
    "y": ("text", "you"),
    "w": ("text", "wall"),
    "s": ("text", "stop"),
    "r": ("text", "rock"),
    "p": ("text", "push"),
    "f": ("text", "flag"),
    "n": ("text", "win"),
}

DIRECTIONS = {
    "left": (0, -1),
    "right": (0, 1),
    "up": (-1, 0),
    "down": (1, 0),
}

NOUNS = frozenset({"baba", "wall", "rock", "flag"})
PROPERTIES = frozenset({"you", "stop", "push", "win"})


class Entity(NamedTuple):
    id: str
    kind: str
    word: str
    row: int
    col: int


def read_map(map_text: str) -> list[str]:
    rows = [line.rstrip("\n") for line in map_text.splitlines() if line.strip()]
    width = max(len(row) for row in rows)
    if any(len(row) != width for row in rows):
        raise ValueError("map rows must be the same width")
    return rows


def generate_facts(map_text: str) -> str:
    """Turn a map into the instance facts baba.lp expects."""
    rows = read_map(map_text)
    facts: list[str] = []
    for row_index, row in enumerate(rows):
        for col_index, symbol in enumerate(row):
            cell = f"l{row_index}_{col_index}"
            facts.append(f"location({cell}).")
            if col_index + 1 < len(row):
                facts.append(f"leftOf({cell}, l{row_index}_{col_index + 1}).")
            if row_index + 1 < len(rows):
                facts.append(f"below(l{row_index + 1}_{col_index}, {cell}).")
            if symbol == ".":
                continue
            if symbol not in LEGEND:
                raise ValueError(f"unknown map symbol {symbol!r}")
            kind, word = LEGEND[symbol]
            name = f"o{row_index}_{col_index}"
            facts.append(f"kind({name}, {kind}).")
            facts.append(f"fluent({name}).")
            facts.append(f"at({name}, {cell}, 0).")
            if word is not None:
                facts.append(f"word({name}, {word}).")
    return "\n".join(facts)


def solve(
    map_text: str,
    *,
    domain_file: Path = DOMAIN_FILE,
) -> list[str]:
    """Return a shortest plan.

    Grounds one new turn at a time. The first satisfiable horizon is the
    shortest plan. Levels are assumed to be solvable.
    """
    control = clingo.Control(["--models=1"])
    control.load(str(domain_file))
    control.add("base", [], generate_facts(map_text))
    control.ground([("base", []), ("meta", [clingo.Number(0)])])

    for horizon in count(1):
        step_time = clingo.Number(horizon)
        control.ground([(name, [step_time]) for name in TURN_PROGRAMS])
        query = clingo.Function("query", [step_time])
        control.assign_external(query, True)
        plan: list[str] = []

        def on_model(model: clingo.Model) -> None:
            plan.extend(_directions(model))

        result = control.solve(on_model=on_model)
        control.release_external(query)
        if result.satisfiable:
            return plan


def _directions(model: clingo.Model) -> list[str]:
    chosen: dict[int, str] = {}
    for symbol in model.symbols(atoms=True):
        if symbol.name != "do":
            continue
        chosen[symbol.arguments[1].number] = str(symbol.arguments[0])
    return [chosen[time] for time in range(1, len(chosen) + 1)]


def won(map_text: str, plan: list[str]) -> bool:
    """Replay a plan and report whether YOU is standing on WIN."""
    rows = read_map(map_text)
    state = _initial_state(rows)
    for direction in plan:
        state = step(state, direction, len(rows), len(rows[0]))
    return _is_won(state)


def step(
    state: tuple[Entity, ...],
    direction: str,
    height: int,
    width: int,
) -> tuple[Entity, ...]:
    """Apply one direction. A move that shifts nothing is rejected."""
    delta_row, delta_col = DIRECTIONS[direction]
    rules = _rules(state)
    by_cell: dict[tuple[int, int], list[Entity]] = {}
    for entity in state:
        by_cell.setdefault((entity.row, entity.col), []).append(entity)

    shifting = {entity.id for entity in state if _has(entity, "you", rules)}
    grew = True
    while grew:
        grew = False
        for entity in state:
            if entity.id not in shifting:
                continue
            ahead = (entity.row + delta_row, entity.col + delta_col)
            for other in by_cell.get(ahead, []):
                if other.id in shifting or not _can_push(other, rules):
                    continue
                shifting.add(other.id)
                grew = True

    def hits_wall(entity: Entity) -> bool:
        next_row = entity.row + delta_row
        next_col = entity.col + delta_col
        if not (0 <= next_row < height and 0 <= next_col < width):
            return True
        for other in by_cell.get((next_row, next_col), []):
            if _has(other, "stop", rules):
                return True
            if _pushable(other, rules) and other.id not in shifting:
                return True
        return False

    frozen: set[str] = set()
    grew = True
    while grew:
        grew = False
        for entity in state:
            if entity.id not in shifting or entity.id in frozen:
                continue
            ahead = (entity.row + delta_row, entity.col + delta_col)
            blocked_by_chain = any(
                other.id in frozen for other in by_cell.get(ahead, [])
            )
            if hits_wall(entity) or blocked_by_chain:
                frozen.add(entity.id)
                grew = True

    moving = shifting - frozen
    if not moving:
        raise ValueError(f"illegal move {direction}")

    return tuple(
        entity._replace(row=entity.row + delta_row, col=entity.col + delta_col)
        if entity.id in moving
        else entity
        for entity in state
    )


def _initial_state(rows: list[str]) -> tuple[Entity, ...]:
    entities: list[Entity] = []
    for row_index, row in enumerate(rows):
        for col_index, symbol in enumerate(row):
            if symbol == ".":
                continue
            kind, word = LEGEND[symbol]
            entities.append(
                Entity(
                    f"o{row_index}_{col_index}", kind, word or "", row_index, col_index
                )
            )
    return tuple(entities)


def _rules(state: tuple[Entity, ...]) -> set[tuple[str, str]]:
    texts = [entity for entity in state if entity.word]
    found: set[tuple[str, str]] = set()
    for subject, middle, prop in _triples(texts):
        if (
            middle.word != "is"
            or subject.word not in NOUNS
            or prop.word not in PROPERTIES
        ):
            continue
        same_row = subject.row == middle.row == prop.row
        reads_right = subject.col + 1 == middle.col and middle.col + 1 == prop.col
        same_col = subject.col == middle.col == prop.col
        reads_down = subject.row + 1 == middle.row and middle.row + 1 == prop.row
        if (same_row and reads_right) or (same_col and reads_down):
            found.add((subject.word, prop.word))
    return found


def _triples(texts: list[Entity]) -> list[tuple[Entity, Entity, Entity]]:
    return [
        (subject, middle, prop)
        for subject in texts
        for middle in texts
        for prop in texts
        if len({subject.id, middle.id, prop.id}) == 3
    ]


def _has(entity: Entity, prop: str, rules: set[tuple[str, str]]) -> bool:
    return (entity.kind, prop) in rules


def _pushable(entity: Entity, rules: set[tuple[str, str]]) -> bool:
    return bool(entity.word) or (entity.kind, "push") in rules


def _can_push(entity: Entity, rules: set[tuple[str, str]]) -> bool:
    return _pushable(entity, rules) and not _has(entity, "stop", rules)


def _is_won(state: tuple[Entity, ...]) -> bool:
    rules = _rules(state)
    yous = [entity for entity in state if _has(entity, "you", rules)]
    wins = [entity for entity in state if _has(entity, "win", rules)]
    return any(
        you.id != win.id and (you.row, you.col) == (win.row, win.col)
        for you in yous
        for win in wins
    )
