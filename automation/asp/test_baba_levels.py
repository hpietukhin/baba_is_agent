"""Two Baba Is You levels solved by baba.lp."""

from pathlib import Path

from automation.asp.baba_solver import solve, won

MAP_DIR = Path(__file__).with_name("maps")
LEVEL0 = (MAP_DIR / "baba_level0.txt").read_text()
LEVEL1 = (MAP_DIR / "baba_level1.txt").read_text()


def test_level0_push_rock_and_touch_flag() -> None:
    # BABA IS YOU and WALL IS STOP are walled in.
    # ROCK IS PUSH and FLAG IS WIN are already active.
    # Baba stands beside the rock, the flag is the next cell.
    # The solver finds the length itself: horizon 1 is too short.
    plan = solve(LEVEL0)
    assert plan == ["right", "right"]
    assert won(LEVEL0, plan)


def test_level1_break_stop_and_assemble_win() -> None:
    # The flag sits in a closed box of walls. WALL IS STOP is a vertical
    # sentence, and Baba starts beside its IS, so one push breaks it.
    # FLAG IS WIN is not a line yet. After the walls stop being STOP,
    # Baba walks through them onto the flag.
    assert not won(LEVEL1, [])
    plan = solve(LEVEL1)
    assert plan is not None
    assert len(plan) == 7
    assert won(LEVEL1, plan)


if __name__ == "__main__":
    test_level0_push_rock_and_touch_flag()
    test_level1_break_stop_and_assemble_win()
    print("level 0:", " ".join(solve(LEVEL0) or []))
    print("level 1:", " ".join(solve(LEVEL1) or []))
