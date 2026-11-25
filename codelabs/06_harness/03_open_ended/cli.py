"""Harness open-ended mode, terminal surface.

    python cli.py "Make me an interactive trip-cost calculator"          asks before render_html runs
    python cli.py "Make me an interactive trip-cost calculator" --yes    approves automatically
"""

import agent
from harness.terminal import run_cli

if __name__ == "__main__":
    run_cli(agent.make_harness)
