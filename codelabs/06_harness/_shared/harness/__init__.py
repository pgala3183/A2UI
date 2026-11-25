"""A small coding-agent-style harness with generative UI.

    tools.py     tools with JSON Schema inputs, validation, permissions and UI output
    loop.py      the agent loop: model turn -> tool calls -> results -> next turn,
                 paused when a tool needs the user's permission
    terminal.py  the terminal surface (rich, ASCII boxes)
    web.py       the web surface: the same events over SSE, plus approve and UI actions

One harness, two surfaces: every event the loop produces is drawn by both.
"""
