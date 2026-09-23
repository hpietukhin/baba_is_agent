"""Solver wrapper: load ASP program, inject facts, extract solution."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from clorm.clingo import Control

from automation.asp.ast_nodes import RuleNode
from automation.asp.fact_generator import generate_facts

_PHILOSOPHY_DIR = Path(__file__).parent
_PHYSICS_LP = _PHILOSOPHY_DIR / "physics.lp"


def solve(
    grid: list[list[str]],
    horizon: int = 20,
    rules: list[RuleNode] | None = None,
    verbose: bool = False,
) -> list[str]:
    """Solve a Baba Is You level given a game grid.

    Args:
        grid: 2D list of cell strings (e.g. [["baba", "", "flag"], ...]).
        horizon: Maximum number of time steps to plan.
        rules: Optional pre-parsed rules. If None, parsed from grid text blocks.
        verbose: Print solver diagnostics.

    Returns:
        Ordered list of action strings (e.g. ["right", "up", "right"]).
        Empty list if no solution found.
    """
    facts = generate_facts(grid, custom_rules=rules)

    ctl = Control()

    # Load static ASP physics program
    ctl.load(str(_PHYSICS_LP))

    # Inject dynamic facts
    ctl.add_facts(facts)

    # Ground
    ctl.ground([("base", [])])

    # Solve and collect actions
    actions: list[str] = []

    def _on_model(model: Any) -> None:
        nonlocal actions
        do_atoms = [
            str(s) for s in model.symbols(atoms=True)
            if str(s).startswith("do(")
        ]
        step_actions: list[tuple[int, str]] = []
        for atom in do_atoms:
            # Parse do(direction,time) from string
            inner = atom[3:-1]  # strip "do(" and ")"
            parts = inner.rsplit(",", 1)
            if len(parts) == 2:
                direction, time_str = parts
                step_actions.append((int(time_str), direction))
        step_actions.sort(key=lambda x: x[0])
        actions = [direction for _, direction in step_actions]

    solve_result = ctl.solve(on_model=_on_model)

    if verbose:
        print(f"Solve result: {solve_result}", file=sys.stderr)

    return actions
