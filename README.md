![Jesse](jesse.png)

Jesse is a lab assistant that runs experiments in scientific software. You describe your research and usual tools in a few Markdown notes, then ask a question. Jesse proposes a plan, an H computer-use agent operates the tools on screen, Python records and analyzes each reading, and Jesse proposes the result with evidence.

Findings describe the tools used, not a physical laboratory.

## Architecture

![Jesse architecture: the Python backend drives one H agent and owns every record; each arrow names its protocol](docs/assets/architecture.png)

Edit [docs/architecture.excalidraw](docs/architecture.excalidraw) in Excalidraw and re-export the PNG.

## Quick start

Requires [uv](https://docs.astral.sh/uv/), Node with pnpm, and an H API key.

```sh
cp .env.example .env          # set HAI_API_KEY
./launch_local.sh             # web; use ./launch_local.sh desktop to work on this Mac
```

The launcher installs dependencies, builds the panel and opens http://127.0.0.1:8765. Try:

| Note | Question |
| --- | --- |
| `research/mechanics.md` | What is the gravity on Planet X? Measure it with the pendulum, and check whether mass changes the result. |
| `research/forest-fire.md` | How does tree density change how much of a forest burns? Compare 55% and 70% density and repeat both. |
| `research/thermochemistry.md` | Compare this new coolant with the reference and explain which absorbs more heat per gram. |

Optional keys in `.env`: `OPENAI_KEY` for the outcome verdict, `GLADIA_API_KEY` for voice, `FISH_API_KEY` for the Pinkman voice.

**Desktop runs** control your own Mac. Grant **Screen & System Audio Recording** and **Accessibility** to your terminal in System Settings → Privacy & Security. Keep your hands off the mouse during the run; press Esc twice to stop H.

## Your research notes

Each file in `research/` describes one research area. Jesse reads them all before every investigation. Copy `research/_template.md` to start; files starting with `_` are ignored.

```markdown
# Classical mechanics

## Background
What you study and the assumptions you work under.

## Usual tools
- **PhET Pendulum Lab**: https://phet.colorado.edu/...
  What it measures, and tips such as which panel shows the reading.

## How I like results
Units, repeats and controls.
```

With these notes, Jesse:

1. Proposes a plan (tool, settings to vary, trials, analysis), then waits about 20 seconds for a correction.
2. Searches the web when it needs a method or reference value, and cites it. It operates only the tools in your notes unless you approve another.
3. Records every reading from the screen and fits or summarizes recorded values with Python.
4. Proposes the result with numbers, units, confidence and a next step.

## The panel

- **Live screen** shows what H sees, with each click marked.
- **Lab notebook** shows each reading and the points Jesse writes down.
- **Agent actions** lists every action with H's stated reason. Click one to rewind the screen and measurements to that step; press ▶ to replay the run.
- **Correct or redirect Jesse** sends a correction to the live session. When you have rewound, the correction refers to that step.
- **Voice**: press the microphone. The first turn starts a run; later turns become corrections. See [live voice setup](docs/LIVE_VOICE.md).
- **History** in the sidebar replays any past run from `runs/`.

Each run ends **supported**, **inconclusive** or **blocked**. An OpenAI model judges the recorded readings and Python analyses against your notes; Python analyses outrank the agent's claims. A run without measurements is blocked.

## Command line

```sh
uv run jesse --notes                                        # list the notes Jesse reads
uv run --env-file .env jesse "question"                     # one investigation in a hosted browser
uv run --env-file .env jesse "question" --surface desktop   # on this Mac
uv run --env-file .env jesse-ui --research path/to/notes    # panel with another notes folder
```

Each run writes `runs/<id>/` with the brief given to H, H events, raw observations, analyses and `report.md`.

## Deployment

```sh
docker compose up --build -d   # http://localhost:8080
```

Containers read `.env` at runtime only and run web surfaces only; desktop control and microphone capture need the local launcher. Set `JESSE_ALLOWED_HOSTS` and `JESSE_PUBLIC_URL` behind a reverse proxy.

Every push to `main` publishes `sha-<commit>` images to GHCR, then bumps `helm/jesse/values.yaml` in the cluster repository. ArgoCD deploys the change to `jesse.adrienpelfresne.com`. The bump needs the `DIRDR_CI_APP_ID` and `DIRDR_CI_APP_PEM` repository secrets.

## Further reading

[AGENT.md](AGENT.md) holds the architecture, decisions and milestone status.
