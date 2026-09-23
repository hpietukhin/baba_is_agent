"""CLI entry point: python -m automation.asp"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _load_grid_from_json(path: Path) -> list[list[str]]:
    """Load a 2D grid from a JSON file with a 'grid' key."""
    data = json.loads(path.read_text())
    if "grid" in data:
        return data["grid"]
    return data


def _print_grid(grid: list[list[str]]) -> None:
    """Pretty-print the game grid."""
    for y, row in enumerate(grid):
        cells = []
        for cell in row:
            if cell:
                short = cell.split("<")[0].removeprefix("text_")
                cells.append(short[:6])
            else:
                cells.append(".")
        print(f"{y + 1:2d} | {' '.join(cells)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ASP solver for Baba Is You",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python -m automation.asp --grid-file state.json
  python -m automation.asp --grid-file state.json --horizon 10 --verbose
  python -m automation.asp --fixture --level 1
""",
    )
    parser.add_argument(
        "--grid-file",
        type=Path,
        help="Path to JSON file containing the game grid",
    )
    parser.add_argument(
        "--fixture",
        action="store_true",
        help="Use built-in test fixture instead of grid-file",
    )
    parser.add_argument(
        "--level",
        type=int,
        default=0,
        help="Level number for fixture mode (default: 0)",
    )
    parser.add_argument(
        "--horizon",
        type=int,
        default=20,
        help="Max planning horizon in time steps (default: 20)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print solver diagnostics",
    )
    parser.add_argument(
        "--show-grid",
        action="store_true",
        help="Display the parsed game grid before solving",
    )

    args = parser.parse_args()

    # Load grid
    if args.fixture:
        fixture_path = (
            Path(__file__).parent.parent.parent
            / ".opencode"
            / "tests"
            / "fixtures"
            / "raw_state.json"
        )
        if not fixture_path.exists():
            print(f"Fixture not found: {fixture_path}", file=sys.stderr)
            sys.exit(1)
        grid = _load_grid_from_json(fixture_path)
    elif args.grid_file:
        if not args.grid_file.exists():
            print(f"File not found: {args.grid_file}", file=sys.stderr)
            sys.exit(1)
        grid = _load_grid_from_json(args.grid_file)
    else:
        parser.error("Either --grid-file or --fixture is required")

    if args.show_grid:
        print("Game grid:")
        _print_grid(grid)
        print()

    # Solve
    from automation.asp.solver import solve

    print(f"Solving with horizon={args.horizon}...")
    actions = solve(grid, horizon=args.horizon, verbose=args.verbose)

    if not actions:
        print("No solution found within the given horizon.")
        sys.exit(1)

    print(f"Solution ({len(actions)} steps):")
    print(f"  Actions: {actions}")
    print(f"  String:  '{','.join(actions)}'")


if __name__ == "__main__":
    main()
