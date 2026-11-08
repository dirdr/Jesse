![Jesse](jesse.png)

Jesse is a lab assistant, a research intern (“stagiaire”), that uses computer use to run experiments in web and desktop scientific software.

You ask a question. Jesse picks a research context, an H agent operates the lab software, Python records each reading, and Jesse writes an evidence-linked report.

## Try it

Requires [uv](https://docs.astral.sh/uv/) and an H API key.

```sh
uv sync
cp .env.example .env  # Only if .env does not already exist.
# Set HAI_API_KEY in .env. Add OPENAI_API_KEY for automatic context selection, GLADIA_API_KEY for voice.
uv run --env-file .env jesse-ui --context chemcollective-coolant
```

Open http://127.0.0.1:8765, then type or speak a question:

> Compare this new coolant with the reference, run the experiment, verify your measurements, and explain which absorbs more heat per gram for the same temperature rise.

The panel shows the live lab screen, H's actions, the plan and each measurement. Send a correction while the session is open. The report opens when the run ends.

`--context` sends every question to one context and skips the selector, so the demo needs no OpenAI key. Without it, Jesse asks the selector to choose among all contexts and blocks questions that none of them supports.

## Past investigations

The left sidebar lists every investigation in `runs/`, newest first. Click one to replay its screens, measurements and report. Use `--runs <folder>` to keep a separate history, for example one per demo.

## Voice

Set `GLADIA_API_KEY` in `.env` and press the microphone button. The first spoken turn starts an investigation; later turns reach the running session as corrections. macOS asks the terminal for microphone access. See [live voice setup](docs/LIVE_VOICE.md) for the noise gate and the terminal preview.

## Add a research context

A research context is one folder in `contexts/`. Jesse loads every folder at startup; names starting with `_` are skipped.

```sh
cp -r contexts/_template contexts/my-lab
# Edit context.toml and protocol.md, then check that Jesse reads it:
uv run jesse --catalogue
uv run --env-file .env jesse-ui --context my-lab
```

| File | Purpose |
| --- | --- |
| `context.toml` | What the lab answers, where it runs, which tools H gets, and its limits |
| `protocol.md` | Step-by-step instructions H follows inside the lab |
| `tools.py` | Optional Python tools for this lab, such as a calculation |

[`contexts/chemcollective-coolant`](contexts/chemcollective-coolant) is a complete example.

### context.toml

```toml
id = "my-lab"                       # lowercase letters, digits, hyphens
title = "What this lab measures"
application = "Name of the software"
questions = ["A question this lab answers."]
unsupported = ["A question it must refuse."]
assumptions = ["Simulator findings only"]
sources = ["https://example.org/docs"]
tools = ["publish_update", "acknowledge_researcher_message", "record_observation"]

[surfaces.web]                      # H's hosted browser
start_url = "https://example.org/lab"

[surfaces.desktop]                  # your own computer
app_path = "/Applications/MyLab.app"

[limits]
budget_seconds = 600                # at most 600
max_steps = 110
max_trials = 2
```

The selector reads `questions`, `unsupported` and `status` to decide whether a question fits. Write them as a researcher would ask.

### Surfaces: web and desktop

Declare one or both.

- **Web**: H opens `start_url` in a hosted browser. Your mouse stays free. Nothing is installed locally.
- **Desktop**: H controls your Mac through the SDK's local bridge (`host = "user_device"`). Install the application first. In **System Settings → Privacy & Security**, enable **Screen & System Audio Recording** and **Accessibility** for the terminal that runs Jesse, then restart it. Keep your hands off the mouse during the run; press **Esc** twice to stop H.

With both declared, Jesse prefers web. Force one with `--surface web` or `--surface desktop` on the `jesse` command.

### Tools

H calls tools to report progress and save readings; Python validates every call.

Built-in tools, enabled by name in `tools`:

| Tool | What H does with it |
| --- | --- |
| `publish_update` | Tells the researcher the plan, a finding, a follow-up or a blocker |
| `acknowledge_researcher_message` | Answers a correction sent from the panel or by voice |
| `record_observation` | Saves displayed values, units, raw text and evidence for one trial |

For lab-specific work, add `tools.py`. Jesse calls `tools(lab)` and gives H every function it returns. H sees each function's name, typed arguments and docstring, so write the docstring as an instruction.

```python
def tools(lab):
    def record_measurement(trial_id: str, value: float, unit: str, raw_reading: str, evidence: list[str]) -> dict:
        """Save one displayed value with its unit, raw text and screenshot evidence."""
        return lab.record(trial_id, {"value": value, "unit": unit, "raw_reading": raw_reading, "evidence": evidence},
                          fields={"Value": f"{value:g} {unit}"}, summary=f"Saved {trial_id}: {value:g} {unit}.")
    return [record_measurement]


def report(lab):
    return "## Summary\n\n" + f"{len(lab.observations())} trial(s) recorded."
```

`lab.record` saves the raw reading once, rejects conflicting retries, enforces `max_trials`, and stores any `analysis` dictionary separately from the raw reading. `fields` and `result` appear in the panel's measurement list. The optional `report(lab)` adds a section to `report.md`. The optional `conclude(lab)` lets Python decide the outcome: return `("supported_conclusion", reason)` once the protocol's completion criteria are met, or `None` to keep the default (`inconclusive` with measurements, `blocked` without). Without it, a run never concludes on its own. The coolant context concludes when two checked estimates agree within 5 % on the same side of the reference. `tools.py` runs as ordinary Python on your machine, so treat it like any other code you install.

## Command line

```sh
uv run jesse --catalogue                                       # list contexts
uv run --env-file .env jesse "question" --context my-lab       # run one context
uv run --env-file .env jesse "question" --plan-only            # choose a context, run nothing
uv run --env-file .env jesse "question" --planner h            # choose with H instead of OpenAI
```

Each run writes `runs/<id>/`: the question, selection, H events, raw observations, analyses and `report.md`. Reports stay **inconclusive** until a person reviews the replay; **blocked** means a required capability or reading was missing.

## Architecture

Python owns sessions, budgets, tools and records. One hosted H agent operates the lab. Solid arrows show implemented paths; dashed arrows show planned ones.

```mermaid
flowchart TB
    U["Researcher"]
    G["Gladia transcription"]
    T["Speech output<br/>Provider to be chosen"]

    subgraph LOCAL["Jesse - local Python application"]
        X["Research contexts<br/>contexts/&lt;id&gt;/"]
        P["Context selector<br/>OpenAI or H, or pinned"]
        C["Controller<br/>Preflight, sessions, budgets and cancellation"]
        K["Tools<br/>Built-in and tools.py"]
        F[("Investigation files<br/>runs/&lt;id&gt;/")]
        O["Markdown report<br/>Outcome, limitations and evidence links"]
        Y["Panel<br/>Live view and history"]
    end

    subgraph HAPI["H managed runtime"]
        H["One H agent<br/>Observe, reason, act and request tools"]
        W["Hosted visual browser"]
        V["Agent View<br/>Live observation and replay"]
    end

    D["Local desktop<br/>user_device bridge"]

    U -->|"Type a question or correction"| Y
    U -->|"Speak"| G
    G -->|"Final turn"| Y
    Y -->|"Start or steer a run"| C
    X -->|"Questions, surfaces, limits"| P
    P -->|"Validated context"| C
    X -->|"Protocol and tools"| C
    C -->|"Start session and return tool results"| H
    H -->|"Stream events and call tools"| K
    K -->|"Validated readings"| F
    H -->|"Operate visible controls"| W
    H -->|"Operate mouse and keyboard"| D
    C -->|"Write outcome"| O
    F -->|"Traceable evidence"| O
    F -->|"History and replay"| Y
    H -->|"Expose session events"| V
    U -->|"Watch live or replay"| V
    C -.->|"Send brief progress updates"| T
    T -.->|"Speak updates"| U
```

Findings describe the configured simulator and its assumptions, not a physical laboratory.
