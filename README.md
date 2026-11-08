![Jesse](jesse.png)

Jesse is a research intern that runs experiments in scientific software. You ask a question; an H computer-use agent operates the lab, Python records and analyzes each reading, and Jesse writes a report linked to its evidence.

Findings describe the simulator and its assumptions, not a physical laboratory.

## Architecture

![Jesse architecture: the Python backend drives one H agent and owns every record; each arrow names its protocol](docs/assets/architecture.png)

Edit [docs/architecture.excalidraw](docs/architecture.excalidraw) in Excalidraw and re-export the PNG.

## Quick start

Requires [uv](https://docs.astral.sh/uv/), Node with pnpm, and an H API key.

```sh
cp .env.example .env          # set HAI_API_KEY
./launch_local.sh chemcollective-coolant web
```

The launcher installs dependencies, builds the panel and opens http://127.0.0.1:8765. Ask:

> Compare this new coolant with the reference, run the experiment, verify your measurements, and explain which absorbs more heat per gram for the same temperature rise.

Optional keys in `.env`: `OPENAI_KEY` for context selection and the outcome verdict, `GLADIA_API_KEY` for voice, `FISH_API_KEY` for the Pinkman voice.

## Demo contexts

| Context | Command | Question |
| --- | --- | --- |
| ChemCollective coolant | `./launch_local.sh chemcollective-coolant web` | Which coolant absorbs more heat per gram? |
| NetLogo Fire | `./launch_local.sh netlogo-fire web` or `desktop` | How does tree density change how much of a forest burns? Compare 55% and 70% and repeat both. |
| PhET Pendulum, Planet X | `./launch_local.sh phet-pendulum web` | What is the gravity on Planet X? Measure it with the pendulum. |

Run a second panel on another port with `PORT=8766 ./launch_local.sh …`.

**Desktop runs** control your own Mac. Install the application, then grant **Screen & System Audio Recording** and **Accessibility** to your terminal in System Settings → Privacy & Security. Keep your hands off the mouse during the run; press Esc twice to stop H.

## The panel

- **Live screen** shows what H sees, with each click marked.
- **Agent decisions** lists every action with H's stated reason. Click one to rewind the screen and measurements to that step; press ▶ to replay the run.
- **Correct or redirect Jesse** sends a correction to the live session. When you have rewound, the correction refers to that step.
- **Voice**: press the microphone. The first turn starts a run; later turns become corrections. See [live voice setup](docs/LIVE_VOICE.md).
- **History** in the sidebar replays any past run from `runs/`.

Each run ends **supported**, **inconclusive** or **blocked**. A context's `outcome(lab)` in `tools.py` decides it in Python from the recorded readings; contexts without one fall back to an OpenAI judgement. A run without measurements is blocked.

## Command line

```sh
uv run jesse --catalogue                                   # list contexts
uv run --env-file .env jesse "question" --context <id>     # run one context
uv run --env-file .env jesse "question" --plan-only        # choose a context only
uv run --env-file .env jesse-ui --context <id> --surface web
```

Without `--context`, a selector picks among all contexts and blocks unsupported questions. Each run writes `runs/<id>/` with H events, raw observations, analyses and `report.md`.

## Add a research context

A context is a folder in `contexts/`; folders starting with `_` are skipped.

```sh
cp -r contexts/_template contexts/my-lab
uv run jesse --catalogue
```

| File | Purpose |
| --- | --- |
| `context.toml` | Supported questions, surfaces (`[surfaces.web]` start URL, `[surfaces.desktop]` app path), tools, completion criteria and limits |
| `protocol.md` | Step-by-step instructions H follows in the lab |
| `tools.py` | Optional: `tools(lab)` returns extra Python tools for H; `report(lab)` adds a report section; `outcome(lab)` decides the outcome |

H sees each tool's name, typed arguments and docstring, so write docstrings as instructions. `lab.record` saves each reading once, rejects conflicting retries and enforces `max_trials`. `tools.py` runs as local Python; review it like any other code.

## Deployment

```sh
docker compose up --build -d   # http://localhost:8080
```

Containers read `.env` at runtime only and run web surfaces only; desktop control and microphone capture need the local launcher. Set `JESSE_ALLOWED_HOSTS` and `JESSE_PUBLIC_URL` behind a reverse proxy.

Every push to `main` publishes `sha-<commit>` images to GHCR, then bumps `helm/jesse/values.yaml` in the cluster repository. ArgoCD deploys the change to `jesse.adrienpelfresne.com`. The bump needs the `DIRDR_CI_APP_ID` and `DIRDR_CI_APP_PEM` repository secrets.

## Further reading

[AGENT.md](AGENT.md) holds the architecture, decisions and milestone status.
