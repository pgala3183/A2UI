"""Harness declarative mode, terminal surface: python cli.py "Make me a rebalancing report" """

import agent
from harness.terminal import run_cli

if __name__ == "__main__":
    run_cli(agent.make_harness)
