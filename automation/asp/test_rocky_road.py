"""Rocky Road, solved by rocky.lp."""

from pathlib import Path

from automation.asp.rocky_solver import MAP_FILE, accepts, parse_level, solve, won

LEVEL = Path(MAP_FILE).read_text()

# Push the left love onto PUSH, send that word across, then walk the
# word down the gap. The middle water is melted on the way.
PLAN = (
    "right up up left left down left left left up right right up "
    "wait down wait down wait down down wait down down down"
).split()


def test_map_matches_the_wiki_frame() -> None:
    level = parse_level(LEVEL)
    assert level.height == 18
    assert level.width == 24
    assert level.flag == (13, 17)
    baba = next(piece for piece in level.pieces if piece.id == "baba")
    assert (baba.row, baba.col) == (9, 7)
    loves = {(piece.row, piece.col) for piece in level.pieces if piece.love}
    assert loves == {(7, 7), (7, 17)}
    assert len(level.rocks) == 28
    assert level.water == frozenset({(10, 16), (10, 17), (10, 18)})
    assert level.sentence == (7, 5)
    assert (11, 17) in level.cells
    assert (5, 5) not in level.cells
    assert (3, 1) not in level.cells


def test_known_plan_wins() -> None:
    assert won(LEVEL, PLAN)
    assert accepts(LEVEL, PLAN)


def test_clingo_solves_rocky_road() -> None:
    plan = solve(LEVEL)
    assert plan is not None
    assert len(plan) == 24
    assert won(LEVEL, plan)


if __name__ == "__main__":
    test_map_matches_the_wiki_frame()
    test_known_plan_wins()
    plan = solve(LEVEL)
    print("rocky road:", " ".join(plan or []))
