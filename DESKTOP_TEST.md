# Run Jesse with NetLogo

The runner supports NetLogo Desktop and NetLogo Web with the same Enzyme Kinetics interaction protocol. Team sequencing: [hackathon plan](docs/HACKATHON_PLAN.md).

## Setup

Python and dependencies are managed with uv:

```sh
uv sync
```

If `.env` does not exist, copy `.env.example` to `.env` and fill `HAI_API_KEY` locally. Gladia is not required for these tests. Secrets and `runs/` are ignored by Git.

## Start from a research question

```sh
uv run --env-file .env jesse "Does adding more substrate make an enzyme reaction faster?" --surface web
```

The default selector uses OpenAI through PydanticAI. Set `OPENAI_KEY` or `OPENAI_API_KEY`; optionally set `OPENAI_MODEL` (default: `gpt-5-mini`). Python validates its selected protocol and surface before starting H. Selection and execution share the `--timeout` budget, which defaults to 300 seconds and cannot exceed 600 seconds.

```sh
uv run jesse --catalogue
uv run --env-file .env jesse "Compare enzyme reaction rates at different substrate quantities" --plan-only
uv run --env-file .env jesse "Compare enzyme reaction rates at different substrate quantities" --planner h
```

`--planner h` uses the existing H key for a tool-only catalogue-selection session; it has no browser or desktop environment. `--plan-only` may call the selected provider but never starts simulator interaction. With `--surface auto` (the default), the selector chooses from surfaces that pass preflight; web is preferred for equivalent capabilities. An explicit web/desktop preference is enforced. Unsupported questions return blocked instead of opening unrelated software.

The catalogue currently contains only the Enzyme Kinetics two-trial feasibility protocol. It does not perform a saturation study or automatically execute follow-ups. Anthropic is not integrated. The direct commands below bypass the selector and require only the H key.

Selection artifacts include `request.json`, `catalogue.json`, `availability.json`, `selection.json` and `planning-metrics.json`. H-backed selection also saves `planner-session.json` and `planner-events.jsonl`. Simulator evidence goes into the same run directory.

## Watch a web run live

```sh
uv run --env-file .env jesse-netlogo --surface web --check
uv run --env-file .env jesse-netlogo --surface web --timeout 300
```

Open the **Agent View URL** printed after session creation. H operates a hosted visual browser, so your own mouse stays available. The check validates local setup; network connectivity, account access and model loading are tested during the real run.

## Watch a native desktop run

NetLogo Desktop must be installed. The runner searches `/Applications` and `~/Applications`, including versioned NetLogo folders. Supply `--netlogo /path/to/NetLogo.app` for another installation location.

```sh
uv run --env-file .env jesse-netlogo --surface desktop --check
uv run --env-file .env jesse-netlogo --surface desktop --timeout 300
```

In macOS **System Settings → Privacy & Security**, enable **Screen & System Audio Recording** and **Accessibility** for the application launching Python: Codex, Terminal or iTerm as applicable. Restart the launching app if requested, then repeat the check. The preflight check does not change permissions or bypass macOS prompts. [Apple permission instructions](https://support.apple.com/guide/mac-help/control-access-screen-system-audio-recording-mchld6aa7d23/mac).

Keep the desktop available for H and avoid simultaneous mouse/keyboard use. Press **Esc twice** to stop H desktop actions. **Ctrl+C** stops the runner on either surface. The default execution budget is ten minutes; `--timeout` accepts 1–600 seconds. A short bounded shutdown follows the execution budget to request cancellation and stop the worker.

## What the core currently does

- Checks dependencies, credential presence and native setup before starting H.
- Supplies shared [agent behavior](src/jesse/instructions.md) and the [operating guide](src/jesse/experiments/netlogo/protocol.md).
- Opens an inline H agent with either a local desktop or hosted visual browser environment.
- Saves session identity and live-view URL before processing actions.
- Streams session events and exposes `record_observation` for readings during execution.
- Validates finite values, conditions, intervals, identifiers and evidence presence; preserves unknown units and unreadable results. Identical retries are idempotent; conflicting readings need a new ID. The controller supplies recording timestamps.
- Stops within the configured execution budget and preserves earlier evidence on failure.
- Separates the agent's account from the controller outcome and replay verification.

## Run artifacts

| File | Contents |
| --- | --- |
| `run.json`, `preflight.json`, `protocol.md` | Selected surface/model/budget, setup checks and supplied instructions. |
| `session.json` | Session ID, Agent View URL and SDK result when returned. |
| `events.jsonl` | Events persisted as they arrive; includes tool calls and provider metrics. |
| `observations/*.json` | Raw trial readings with stable IDs, settings, units and evidence descriptions. |
| `analyses/*.json`, `analyses/*.md` | Checked Python comparisons, excluded readings, limitations and suggested follow-ups. |
| `evidence-index.json` | Observation tool calls mapped to actual event lines, timestamps and session replay. |
| `metrics.json` | Elapsed time, first event/observation latency, observation counts and provider metrics when available. |
| `agent-report.md` | The agent's unverified account and interpretation. |
| `outcome.json`, `report.md` | Controller outcome, evidence links and pending verification. |

A successful API turn remains **inconclusive pending replay review**. Check actual parameter changes, model execution, readable values and matching settings in Agent View. Agent-supplied evidence descriptions are not exported screenshots. No screenshot files are fabricated. Two trials establish neither a saturation plateau nor real laboratory validation.

The agent can call a bounded Python rate-comparison tool after recording its trials. Full application selection, scientific inference, autonomous follow-up and voice remain later slices. There is no product UI yet; use the CLI, Agent View and Markdown reports.

To analyze a saved run without starting H or controlling a simulator:

```sh
uv run jesse-analyze runs/YOUR_RUN_DIRECTORY
```

The analyzer checks the assay's fixed settings, 0–30 tick interval, quantity and units before comparing rates. It reports mismatches, excludes unreadable records and saves separate JSON/Markdown artifacts. Its suggestions do not execute further GUI trials. Raw observations and the investigation outcome remain unchanged.

## Performance comparison

Run each surface with the same model, H model and timeout. Compare readable trial completion before latency; inspect provider steps/costs in metrics when available. A blocked desktop preflight has no meaningful agent runtime to compare. Cloud browser versus local desktop timings also include different infrastructure and startup costs. Use repeated runs before drawing performance conclusions.

## Current evidence

The first live web run (`20261107T120115764135Z`) took about 213 seconds and recorded two rates, 1.276 and 2.241, at substrate settings 50 and 100. Those are agent-recorded observations awaiting replay review, not a validated scientific result. That first run predates controller-supplied timestamps; its agent-supplied `observed_at` fields are unreliable. Use the event timestamps instead.

Native preflight found `/Applications/NetLogo 7.0.4/NetLogo 7.0.4.app` and passed Accessibility; Screen Recording remained blocked. No native performance result is established.

The second live web run (`20261107T122354074237Z`) took about 101 seconds. H recorded both trials, called the Python analyzer and included its result in the report. The analyzer returned `not_comparable` because the recorded units were unknown. This verifies the live tool path, not the scientific comparison. Confirm the documented rate definition and units before the full experiment.

The question-driven path was then exercised through OpenAI selection, H execution and analysis. One run exposed malformed settings arguments; the tool now takes scalar control values and Python assembles the observation. The corrected run (`20261107T130453990066Z`) saved both readings. Its unspecified unit label is rejected by the tightened analyzer. Original observations remain unchanged.

The [measurement definition](src/jesse/experiments/netlogo/measurement.md) now documents the model's V proxy, source-derived units and timing convention. New runs receive that definition. The analyzer still rejects unknown or unspecified unit labels. Source inspection supplies assumptions, not experimental readings or scientific verification.

Run automated checks with:

```sh
uv run python -m unittest discover -s tests -v
```

Test numerical readings are explicitly synthetic and do not establish GUI feasibility.
