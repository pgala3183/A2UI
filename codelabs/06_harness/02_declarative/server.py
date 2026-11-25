"""Harness declarative mode, web surface (the terminal mirrors it).

    python server.py            then open http://127.0.0.1:8602
    python cli.py "Make me a rebalancing report"     the terminal surface alone
"""

import agent
from genui_common.web import port_from_argv
from harness.web import make_app

app = make_app(agent.HERE, agent.make_harness, "Harness declarative")

if __name__ == "__main__":
    app.run(port_from_argv(8602))
