"""Harness mixed mode, terminal surface: python cli.py "Build me a rebalancing desk" """

import agent
from harness.terminal import run_cli

if __name__ == "__main__":
    run_cli(agent.make_harness)
