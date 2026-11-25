"""Harness static mode, terminal surface: python cli.py "Which stations need rebalancing?" """

import agent
from harness.terminal import run_cli

if __name__ == "__main__":
    run_cli(agent.make_harness)
