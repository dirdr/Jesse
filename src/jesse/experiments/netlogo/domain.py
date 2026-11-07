"""NetLogo investigation protocol; independent of SDK and storage."""
PROMPT = """Operate only NetLogo Desktop using screenshots, mouse and keyboard.
Open the bundled Enzyme Kinetics model through File > Models Library.
Inspect and record the visible settings. Set Kr to a nonzero value and enable
PAUSE? so runs stop after 30 ticks. Run SETUP, GO, then RECORD V.
Read the resulting rate and settings. Repeat with a different VOLUME, holding
Kc, Kd and Kr fixed, using SETUP, GO and RECORD V again.
Do not use the command center, scripting, shell, or a browser replacement.
Report actual settings and observations, screenshots/session evidence references,
and any limitations. If numerical readings are unreadable, report blocked rather
than guessing. This is an interaction test, not proof of saturation from two points.
Stop after these two trials or on a blocker. Return a short scientific Markdown
report with method, observations, comparison, limitations and outcome.
"""

