# Videos

One video per part: Part 0 (setup and shared plumbing) and one per technology. Each technology video has four chapters, one per mode (static, declarative, open-ended, mixed). Every script below lists what to show on screen, the commands to run, the code to highlight and what to say.

| Part | Script | Length (target) | YouTube link |
|---|---|---|---|
| 0 · Setup and shared plumbing | [00_setup_and_plumbing.md](scripts/00_setup_and_plumbing.md) | 10 min | _add link after upload_ |
| 1 · A2UI | [01_a2ui.md](scripts/01_a2ui.md) | 20 min | _add link after upload_ |
| 2 · AG-UI | [02_ag_ui.md](scripts/02_ag_ui.md) | 20 min | _add link after upload_ |
| 3 · MCP Apps | [03_mcp_apps.md](scripts/03_mcp_apps.md) | 20 min | _add link after upload_ |
| 4 · json-render | [04_json_render.md](scripts/04_json_render.md) | 18 min | _add link after upload_ |
| 5 · OpenUI Lang | [05_openui.md](scripts/05_openui.md) | 18 min | _add link after upload_ |
| 6 · Harness integration | [06_harness.md](scripts/06_harness.md) | 20 min | _add link after upload_ |

If you prefer one video per codelab (24 short videos), each chapter of a script is a complete 4 to 6 minute video on its own.

## Recording setup

- **Recorder:** OBS Studio (free) or the Windows Snipping Tool screen recorder (Win+Shift+R). 1920x1080, 30 fps, microphone on, system audio off.
- **Layout:** editor (VS Code) on the left two thirds, terminal at the bottom of the editor; browser on the right third or in a second scene. Zoom the editor to 140% and the terminal font to 16 pt so code is readable on a phone.
- **Before recording a part:** `python run_all.py codelabs/<theme>` (all green), close other tabs, start each server only when its chapter begins (`Ctrl+C` to stop it).
- **Slow streaming for the camera:** set `GENUI_DELAY=0.05` before `python server.py` so the audience can watch components arrive. PowerShell: `$env:GENUI_DELAY = "0.05"`.
- **The wire panel** on the right of every page lists each message that crossed the network. Point at it whenever a new message type appears: it is the protocol, live.

## A chapter has the same five beats

1. **The idea (30 s):** the mode in one sentence and the diagram from the codelab README.
2. **Run it (60 s):** `python demo.py`, then `python server.py` and use the page. Show the wire panel.
3. **Walk the code (2-3 min):** open the files in the order of the README's "Code walkthrough"; highlight the lines quoted there.
4. **Prove it (30 s):** `python -m pytest -q` in the codelab folder; name one test and what it guarantees.
5. **Takeaway (15 s):** the one sentence in the script.

## Upload checklist

- Title: `GenUX codelabs · Part N · <Technology>: static, declarative, open-ended and mixed generative UI`
- Description: one paragraph, the repository link `https://github.com/pgala3183/A2UI`, and chapter timestamps (`0:00 Intro`, `2:10 Static`, ...).
- Paste the link into the table above and into the theme README, then commit.
