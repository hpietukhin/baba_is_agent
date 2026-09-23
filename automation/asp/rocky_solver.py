"""Solve the Rocky Road map with the shared encoding in baba.lp."""

from __future__ import annotations

from collections import deque
from itertools import count
from pathlib import Path
from typing import NamedTuple

import clingo

from automation.asp.baba_solver import TURN_PROGRAMS

DOMAIN_FILE = Path(__file__).with_name("baba.lp")
MAP_FILE = Path(__file__).with_name("maps") / "rocky_road.txt"

# Text Baba can push: inside the room, under the top wall and above the bottom one.
# The same glyphs above and below that ring draw sentences Baba cannot reach.
_ROOM_LO = 4
_ROOM_HI = 10
_TEXT = {"v": "love", "i": "is", "t": "tele", "P": "push"}
_GLYPH = {
    "b": "baba",
    "i": "is",
    "y": "you",
    "k": "rock",
    "d": "defeat",
    "f": "flag",
    "n": "win",
    "v": "love",
    "t": "tele",
    "l": "wall",
    "s": "stop",
    "w": "water",
    "m": "melt",
    "a": "and",
    "h": "hot",
    "P": "push",
}
_DELTAS = {
    "left": (0, -1),
    "right": (0, 1),
    "up": (-1, 0),
    "down": (1, 0),
    "wait": (0, 0),
}


class Piece(NamedTuple):
    id: str
    row: int
    col: int
    word: str
    love: bool


class Level(NamedTuple):
    walls: frozenset[tuple[int, int]]
    rocks: frozenset[tuple[int, int]]
    cells: frozenset[tuple[int, int]]
    flag: tuple[int, int]
    sentence: tuple[int, int]
    height: int
    width: int
    pieces: tuple[Piece, ...]
    water: frozenset[tuple[int, int]]


def read_map(map_text: str) -> list[str]:
    rows = [
        line
        for line in map_text.splitlines()
        if line.strip() and not line.startswith("%")
    ]
    width = max(len(row) for row in rows)
    if any(len(row) != width for row in rows):
        raise ValueError("map rows must be the same width")
    return rows


def parse_level(map_text: str) -> Level:
    """Read walls, rocks, water, the flag, Baba, the loves, and room text."""
    rows = read_map(map_text)
    walls: set[tuple[int, int]] = set()
    rocks: set[tuple[int, int]] = set()
    water: set[tuple[int, int]] = set()
    flag: tuple[int, int] | None = None
    pieces: list[Piece] = []
    loves: list[tuple[int, int]] = []
    texts: list[tuple[int, int, str]] = []

    for row_index, row in enumerate(rows):
        for col_index, symbol in enumerate(row):
            cell = (row_index, col_index)
            if symbol == ".":
                continue
            if symbol == "#":
                walls.add(cell)
            elif symbol == "R":
                rocks.add(cell)
            elif symbol == "~":
                water.add(cell)
            elif symbol == "F":
                flag = cell
            elif symbol == "B":
                pieces.append(Piece("baba", row_index, col_index, "", False))
            elif symbol == "H":
                loves.append(cell)
            elif symbol in _TEXT and _ROOM_LO <= row_index <= _ROOM_HI:
                texts.append((row_index, col_index, _TEXT[symbol]))
            elif symbol in _TEXT or symbol in "bykdfnlswmah":
                continue
            else:
                raise ValueError(f"unknown map symbol {symbol!r}")

    if flag is None:
        raise ValueError("map has no flag")
    if sum(piece.id == "baba" for piece in pieces) != 1:
        raise ValueError("map must contain one Baba")
    if len(loves) != 2:
        raise ValueError("map must contain two loves")

    for (row_index, col_index), name in zip(
        sorted(loves), ("left", "right"), strict=True
    ):
        pieces.append(Piece(name, row_index, col_index, "", True))

    push_cells = [
        (row_index, col_index) for row_index, col_index, word in texts if word == "push"
    ]
    if len(push_cells) != 1:
        raise ValueError("map must contain one PUSH word inside the room")
    pieces.append(Piece("push", push_cells[0][0], push_cells[0][1], "push", False))
    # LOVE / IS / TELE stay put, so their cells are not floor.
    fixed = {
        (row_index, col_index) for row_index, col_index, word in texts if word != "push"
    }
    cells = _reachable(
        len(rows),
        len(rows[0]),
        walls | fixed,
        {(piece.row, piece.col) for piece in pieces} | {flag} | water,
    )

    return Level(
        frozenset(walls),
        frozenset(rocks),
        cells,
        flag,
        push_cells[0],
        len(rows),
        len(rows[0]),
        tuple(pieces),
        frozenset(water),
    )


def generate_facts(map_text: str) -> str:
    """Turn Rocky Road into the instance facts baba.lp expects.

    Baba, the two loves and PUSH move. Every other word stays in fixed_at,
    and the sentences are read by meta(t). Walls are cells, blocked while
    WALL IS STOP holds.
    """
    level = parse_level(map_text)
    rows = read_map(map_text)
    fixed = _fixed_text(rows)
    locations = set(level.cells) | set(level.walls) | {cell for cell, _word in fixed}
    facts = ["dir(wait)."]
    for row, col in sorted(locations):
        facts.append(f"location({_cell(row, col)}).")
    for row, col in sorted(locations):
        if (row, col + 1) in locations:
            facts.append(f"leftOf({_cell(row, col)}, {_cell(row, col + 1)}).")
        if (row + 1, col) in locations:
            facts.append(f"below({_cell(row + 1, col)}, {_cell(row, col)}).")
    facts.extend(f"wall({_cell(row, col)})." for row, col in sorted(level.walls))
    facts.extend(f"rock({_cell(row, col)})." for row, col in sorted(level.rocks))
    facts.extend(f"water0({_cell(row, col)})." for row, col in sorted(level.water))
    facts.append(f"flag({_cell(*level.flag)}).")
    for piece in level.pieces:
        facts.append(f"fluent({piece.id}).")
        facts.append(f"at({piece.id}, {_cell(piece.row, piece.col)}, 0).")
        if piece.love:
            facts.append(f"kind({piece.id}, love).")
        elif piece.word:
            facts.append(f"kind({piece.id}, text).")
            facts.append(f"word({piece.id}, {piece.word}).")
        else:
            facts.append(f"kind({piece.id}, baba).")
    for (row, col), word in fixed:
        name = f"t{row}_{col}"
        facts.append(f"kind({name}, text).")
        facts.append(f"word({name}, {word}).")
        facts.append(f"fixed_at({name}, {_cell(row, col)}).")
    return "\n".join(facts)


def solve(
    map_text: str,
    *,
    domain_file: Path = DOMAIN_FILE,
) -> list[str]:
    """Return a shortest plan. Levels are assumed to be solvable."""
    found = _search(map_text, domain_file=domain_file, plan=None)
    assert found is not None
    return found


def accepts(
    map_text: str,
    plan: list[str],
    *,
    domain_file: Path = DOMAIN_FILE,
) -> bool:
    """True when Clingo agrees that this exact plan wins."""
    found = _search(map_text, domain_file=domain_file, plan=plan)
    return found == plan


def _search(
    map_text: str,
    *,
    domain_file: Path,
    plan: list[str] | None,
) -> list[str] | None:
    control = clingo.Control(["--models=1"])
    control.load(str(domain_file))
    control.add("base", [], generate_facts(map_text))
    control.ground([("base", []), ("meta", [clingo.Number(0)])])

    forced = plan if plan is not None else []
    horizons = range(1, len(forced) + 1) if plan is not None else count(1)
    for horizon in horizons:
        step_time = clingo.Number(horizon)
        control.ground([(name, [step_time]) for name in TURN_PROGRAMS])
        if forced:
            control.add(
                f"fix{horizon}", [], f":- not do({forced[horizon - 1]}, {horizon})."
            )
            control.ground([(f"fix{horizon}", [])])
        if forced and horizon != len(forced):
            continue
        query = clingo.Function("query", [step_time])
        control.assign_external(query, True)
        chosen: list[str] = []

        def on_model(model: clingo.Model) -> None:
            chosen.extend(_directions(model))

        result = control.solve(on_model=on_model)
        control.release_external(query)
        if result.satisfiable:
            return chosen
    return None


def _directions(model: clingo.Model) -> list[str]:
    chosen: dict[int, str] = {}
    for symbol in model.symbols(atoms=True):
        if symbol.name != "do":
            continue
        chosen[symbol.arguments[1].number] = str(symbol.arguments[0])
    return [chosen[time] for time in range(1, len(chosen) + 1)]


def won(map_text: str, plan: list[str]) -> bool:
    """Replay a plan and report whether Baba is standing on the flag."""
    level = parse_level(map_text)
    pieces, water = level.pieces, level.water
    for direction in plan:
        stepped = step(level, pieces, water, direction)
        if stepped is None:
            return False
        pieces, water = stepped
    return _baba(pieces) == level.flag


def step(
    level: Level,
    pieces: tuple[Piece, ...],
    water: frozenset[tuple[int, int]],
    direction: str,
) -> tuple[tuple[Piece, ...], frozenset[tuple[int, int]]] | None:
    """Apply one action. Illegal moves and defeat return None."""
    delta_row, delta_col = _DELTAS[direction]
    pushing = _push_on(pieces, level.sentence)
    by_cell: dict[tuple[int, int], list[Piece]] = {}
    for piece in pieces:
        by_cell.setdefault((piece.row, piece.col), []).append(piece)

    def pushable(piece: Piece) -> bool:
        return piece.id == "push" or (piece.love and pushing)

    if direction == "wait":
        moved = pieces
    else:
        shifting = {"baba"}
        grew = True
        while grew:
            grew = False
            for piece in pieces:
                if piece.id not in shifting:
                    continue
                ahead = (piece.row + delta_row, piece.col + delta_col)
                for other in by_cell.get(ahead, []):
                    if other.id in shifting or not pushable(other):
                        continue
                    shifting.add(other.id)
                    grew = True

        frozen: set[str] = set()
        grew = True
        while grew:
            grew = False
            for piece in pieces:
                if piece.id not in shifting or piece.id in frozen:
                    continue
                ahead = (piece.row + delta_row, piece.col + delta_col)
                blocked = ahead not in level.cells or any(
                    other.id in frozen or (pushable(other) and other.id not in shifting)
                    for other in by_cell.get(ahead, [])
                )
                if blocked:
                    frozen.add(piece.id)
                    grew = True

        moving = shifting - frozen
        if "baba" not in moving:
            return None
        moved = tuple(
            piece._replace(row=piece.row + delta_row, col=piece.col + delta_col)
            if piece.id in moving
            else piece
            for piece in pieces
        )

    water = water - {(piece.row, piece.col) for piece in moved if piece.love}
    moved = _teleport(moved)
    if _baba(moved) in level.rocks or _baba(moved) in water:
        return None
    return moved, water


def _cell(row: int, col: int) -> str:
    return f"l{row}_{col}"


def _fixed_text(rows: list[str]) -> list[tuple[tuple[int, int], str]]:
    found: list[tuple[tuple[int, int], str]] = []
    for row_index, row in enumerate(rows):
        for col_index, symbol in enumerate(row):
            if symbol not in _GLYPH or symbol == "P":
                continue
            found.append(((row_index, col_index), _GLYPH[symbol]))
    return found


def _push_on(pieces: tuple[Piece, ...], sentence: tuple[int, int]) -> bool:
    push = next(piece for piece in pieces if piece.id == "push")
    return (push.row, push.col) == sentence


def _teleport(pieces: tuple[Piece, ...]) -> tuple[Piece, ...]:
    loves = [piece for piece in pieces if piece.love]
    if len(loves) != 2:
        return pieces
    left, right = loves
    if (left.row, left.col) == (right.row, right.col):
        return pieces
    homes = {
        (left.row, left.col): (right.row, right.col),
        (right.row, right.col): (left.row, left.col),
    }
    swapped: list[Piece] = []
    for piece in pieces:
        if piece.love:
            swapped.append(piece)
            continue
        dest = homes.get((piece.row, piece.col))
        if dest is None:
            swapped.append(piece)
        else:
            swapped.append(piece._replace(row=dest[0], col=dest[1]))
    return tuple(swapped)


def _baba(pieces: tuple[Piece, ...]) -> tuple[int, int]:
    baba = next(piece for piece in pieces if piece.id == "baba")
    return baba.row, baba.col


def _reachable(
    height: int,
    width: int,
    blocked: set[tuple[int, int]],
    seeds: set[tuple[int, int]],
) -> frozenset[tuple[int, int]]:
    seen: set[tuple[int, int]] = set()
    queue: deque[tuple[int, int]] = deque(seeds)
    while queue:
        cell = queue.popleft()
        if cell in seen or cell in blocked:
            continue
        row, col = cell
        if not (0 <= row < height and 0 <= col < width):
            continue
        seen.add(cell)
        queue.extend(((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)))
    return frozenset(seen)
