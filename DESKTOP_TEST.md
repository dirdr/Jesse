# NetLogo desktop test

NetLogo Desktop must be installed. Manage Python and dependencies with uv:

```sh
cp .env.example .env
# Fill HAI_API_KEY and GLADIA_API_KEY in .env locally.
uv sync
uv run --env-file .env jesse-netlogo
```

Only HAI_API_KEY is required for the desktop test. Gladia is reserved for voice.
The real .env and run artifacts are ignored by Git.

The `experiments/netlogo` vertical slice co-locates its protocol, application
use case, boundary protocols, H/filesystem adapters and CLI composition root.
The domain and application modules have no provider dependencies.

Grant Screen Recording and Accessibility permissions to the terminal launching
Python when macOS requests them, then rerun. H controls the actual desktop;
keep NetLogo visible and avoid simultaneous mouse/keyboard use. Press Esc twice
to stop desktop actions. The runner closes its connection after ten minutes.

Ignored `runs/` directories contain session results and Markdown reports.
The full SDK result is preserved, including session/view metadata where supplied.
Confirm that the result contains a session ID and live/replay URL; inspect Agent
View for evidence. Screenshot export and metadata normalization remain follow-up
work pending a real SDK session. Do not treat a generated report alone as proof:
verify the two GUI trials and readings in the session replay.

This test has not yet been executed successfully against H. Dependency installation
in the development sandbox was blocked by DNS resolution of pypi.org.
