# Scenario-first build plan

Status: working proposal for three people, 24 hours until submission and approximately eight focused implementation hours as of initial planning. NetLogo desktop and web feasibility are authorized; later product choices remain open in [AGENT.md](../AGENT.md). Owners below are roles until teammates are assigned.

## The story to demonstrate

Researcher: “Does adding more ingredient always make this reaction faster?”

Jesse selects the supported NetLogo experiment, explains its plan, operates the desktop, records measurements, compares rates, checks a surprising result and produces a report linked to the evidence. Explain enzyme as the processing machine and substrate as the ingredient.

NetLogo is the first engineering scenario. Coolant remains the preferred public story in the project brief; promote it only after a separate GUI feasibility test. Keep the NetLogo demo ready if that test fails. Algodoo follows later.

The presentation should show these beats:

1. Ask the question in text; use voice after that path works.
2. Show Jesse choosing the model and stating what it will vary and hold fixed.
3. Show a real parameter change, simulation and reading in Agent View.
4. Show a measurement table and rate comparison from Python.
5. Introduce a labelled challenge: “I think that last result was taken under different conditions. Please check.” Jesse examines the evidence and repeats a relevant trial. Report a discrepancy only if the evidence establishes one.
6. Open the Markdown report and follow a measurement back to its evidence.

The agent must be able to conclude inconclusive. A polished story never substitutes for actual readings.

## Build gates

Follow the construction sequence in AGENT.md. This table turns it into team deliverables, rather than marking untested work complete.

| Gate | Build and demonstrate | Acceptance evidence |
| --- | --- | --- |
| G0: desktop proof, first priority | Run the existing `jesse-netlogo` entry point with the bounded operating guide. Repair SDK/permission/reading blockers. | Two trials with different substrate settings and fixed reaction constants; actual control change, run and readable result; session ID, Agent View URL and evidence matching each trial. Ten-minute cap. |
| G1: selection and records | Explicit catalogue entry for NetLogo; reject unsupported requests; persist raw observations as they arrive. | Supported request selects NetLogo; unsupported request explains its missing capability; duplicate writes do not duplicate observations; interrupted run retains prior evidence. |
| G2: scientific workflow | Predefine a rate measure and comparable interval; run a small substrate sweep with repeats; Python analysis informs one follow-up. | Measurements with conditions and units, plot/table, documented comparison rule and an observed follow-up. Calibrate trial count and budget using G0 timings before starting. |
| G3: Result Detective | Detect a condition mismatch or an anomalous reading, then inspect or repeat within the budget. | Preserve original data; record why the follow-up was chosen and whether it resolved the concern. Exercise unavailable reading and exhausted budget too. |
| G4: voice and presentation | Connect final Gladia utterances to the working controller; add agreed speech output; render and rehearse the report. | Spoken correction changes a later action in the same investigation; acknowledgement appears; report evidence resolves; supported, inconclusive and blocked outcomes rehearsed. |

G0 establishes interaction feasibility. Two measurements cannot establish saturation. G2 needs several levels, repeat measurements and an explicit assessment of variability; accept inconclusive if those do not support a plateau.

## Responsibility split

Three owners, each delivering a runnable path and a fixture for teammates. Suggested assignment: project lead takes A; teammates take B and C according to preference.

| Owner | First task, can start now | Delivery and boundary |
| --- | --- | --- |
| A: H and desktop, integration lead | Run G0 on the demo machine; record the exact SDK version, permissions, failures and timings. | Own `experiments/netlogo` runner and H adapter. Deliver replay and two evidenced trials. Later expose one active session for corrections and persist metadata before waiting for completion. |
| B: experiment, analysis and report | Manually inspect the installed model, identify a readable rate output and its definition, propose measurement levels and repeat policy; render a fixture report. | Own protocol, catalogue, analysis and report slices. Deliver analyzer accepting recorded data, returning comparisons, limitations and a follow-up request; render Markdown with evidence links. Label synthetic fixtures; only observed data supports claims. |
| C: Gladia, personality and presentation | Microphone → transcription → final text event, with a console consumer; prepare concise spoken updates and the demo script. | Own voice slice and rehearsal. Deliver final utterances, deduplication, error handling and a recorded test phrase. No NetLogo/H dependency for first task. Integrate corrections with A after G2; select speech output separately. Start with Agent View and an existing Markdown viewer. |

If B falls behind, C takes report presentation while B retains scientific validation. A owns shared controller changes; C submits voice events through the agreed boundary.

One person controls the demo desktop at a time. Teammates use fixtures, their own machines or read-only replay. A remains the sole custom-tool executor.

## Handoffs to agree before parallel implementation

Use [TEAM_CONTRACTS.md](TEAM_CONTRACTS.md) as the proposed payload contract. These are data boundaries, not a new orchestration framework or service deployment.

- C → A: one final text event per utterance. Text entry uses the same controller path.
- A → B: immutable observation with settings, readable output, units and evidence.
- B → A: analysis and a bounded follow-up suggestion; H chooses the GUI actions.
- A → B's renderer: raw observations, derived analysis, outcome and resolvable evidence.
- B → C: a rendered report and traceable results for rehearsal.

Keep domain code in use-case slices under `src/jesse`; compose provider adapters at each entry point as required by AGENT.md.

## First team work session

1. Assign A–C and confirm working language and the rehearsal machine. English text is a provisional starting point, not a final language decision.
2. A follows [DESKTOP_TEST.md](../DESKTOP_TEST.md). B checks the model's visible outputs independently, then relinquishes the shared desktop. C begins the isolated voice path.
3. At G0 review, inspect replay against every acceptance criterion. Record pass, blocked or inconclusive and the exact blocker. Do not advance based on the agent's summary alone.
4. Use observed interaction times to choose G2 trial count and budget. Agree on the data contract before implementing recording and analysis.
5. Integrate at G1/G2 before adding voice to the shared runtime. Reserve the final quarter of available hackathon time for integration and rehearsal; cut extra simulators and UI first if behind.

## Eight focused implementation hours

Times are elapsed working time after the team starts, not wall-clock deadlines. Leave the remaining submission window for breaks, packaging and contingency.

| Time | A: runtime | B: science/report | C: voice/demo | Checkpoint |
| --- | --- | --- | --- | --- |
| 0–1 h | Run G0; fix connection and permissions. | Verify visible measurement and protocol; prepare labelled fixture. | Capture a spoken question as one final text event. | Replay proves two GUI trials, or name a specific blocker. |
| 1–3 h | Stream/persist evidence; select the NetLogo experiment; validate observations. | Build analyzer and report against the contract. | Deduplicate transcripts; prepare persona examples and voice errors. | G1, plus analyzer and renderer consume the same fixture. |
| 3–5 h | Connect observations → analysis → one follow-up. | Check real data, repeat policy, units and report links. | Prepare correction handoff with A and select/test speech output. | G2 real experiment/report; freeze new feature scope. |
| 5–6 h | Integrate correction and recovery. | Verify discrepancy handling and incomplete outcomes. | Demonstrate spoken correction and short acknowledgement. | G3/G4 integration; text stays available if voice fails. |
| 6–8 h | Fix integration defects and capture actual replay. | Audit report/evidence and scientific claims. | Rehearse, record backup demo and prepare submission. | Complete a timed demo twice; label any replay honestly. |

If G0 is still blocked after hour 1, A and B focus on that blocker while C continues voice. If no readable measurement is possible, present the limitation honestly or test another already-approved scenario; never replace readings with fixtures. A second simulator, custom UI and optional reviewer are stretch work only after rehearsal succeeds.

## Extensibility without expanding this demo

Treat each supported investigation as an experiment definition: stable ID, supported questions, application/environment, operating guide, settings/measurement schema, assumptions, analyzer, completion criteria and tested interaction status. See [the definition contract](TEAM_CONTRACTS.md#experiment-definition).

Keep the controller responsible for run/session lifecycle, budgets, event routing and persistence. Keep application-specific controls and science in the experiment slice. H consumes the chosen definition and guides GUI actions. Add another lab activity by implementing and testing its definition, protocol and analysis; a new interaction surface may also need an environment adapter. Every new definition must pass its own G0.

The first implementation can use a small Python mapping of definitions. Avoid building plugin discovery before a second experiment needs it. NetLogo's two-trial feasibility entry point stays available as a diagnostic even after the general investigation entry point exists.

## Orchestration and multiple agent APIs

Retain the accepted MVP boundary: one hosted H operator and a lightweight Python controller. The controller moves through select → plan → measure → analyze → verify → report, with explicit blocked and budget-exhausted exits. H decides the experimental follow-up; Python validates and computes. Voice enters as researcher input at the same boundary as text.

Use a session handle for live metadata, event persistence and steering. H's documented extension points support instructions, skills, custom tools and structured answers; first use those rather than adding another orchestration framework. [Agent configuration](https://hub.hcompany.ai/agents-api/agents/overview).

Multiple agent API providers are possible behind narrow adapters, but are optional. A later reviewer could receive evidence and derived results, return a critique, and let the same operator decide on a follow-up. Keep the reviewer read-only and bounded; preserve one owner of desktop actions and tool execution. Document a measured benefit before adding its cost and failure modes. This is a future option, not a reversal of the accepted single-agent decision.

## Tone, personality and spoken updates

Use the calm lab-colleague personality in AGENT.md. C owns wording and speech presentation; A owns when updates are emitted. The shared [agent instructions](../src/jesse/instructions.md) are loaded with the experiment guide, so personality applies to execution as well as the demo script.

Announce plans, noteworthy observations, follow-ups and blockers. Keep spoken updates to one or two sentences and avoid narrating each click. Describe what is known before interpreting it. Keep technical detail and all measurement values in the report. Examples:

- Plan: “I'll change the ingredient amount and keep the reaction settings fixed.”
- Check: “These measurements may not be comparable. I'll check the settings before repeating the trial.”
- Correction: “Understood. I'll apply that change to the next trial and keep the earlier measurements.”
- Blocked: “I can run the model, but I can't read the rate reliably. I need a readable output before I can compare the trials.”

Gladia supplies transcription in the current design. Speech output remains a separate choice; C should select a provider or local option and test it early, with captions available. A spoken correction is not a hard real-time emergency stop; retain the desktop stop mechanism.

## Demo readiness checklist

The demo should show a question becoming an experiment, a checked comparison, a justified follow-up, and a report with evidence. Checked items have implementation or recorded-run evidence; they do not imply that an entire gate has passed. G0 replay acceptance and the full G2 investigation remain open. G1 catalogue routing and record persistence are implemented.

### Available foundations

- [x] Start a bounded H session on an explicit web or desktop surface.
- [x] Publish Agent View for live observation and replay.
- [x] Persist session identity, events and readings during execution.
- [x] Reject invalid readings and conflicting retries; preserve unknown values.
- [x] Record two web GUI trials with distinct substrate settings and numerical outputs.
- [x] Preserve partial evidence and write blocked/inconclusive reports.
- [x] Compare saved rates with Python after checking settings, quantities, units and intervals.
- [x] Save derived analysis separately and recommend checks or independent repeats.
- [x] H calls the analyzer during a live web run and reports its validation result. The second live run returned `not_comparable` because rate units were unknown.
- [x] Register the first protocol, accept a research question, and validate the proposed protocol and available surface. Both OpenAI and H selection backends have passed live routing checks; H also blocked an unsupported coolant request.
- [x] Exercise question → OpenAI selection → H GUI trials → persisted observations → Python analysis → report. Harden the observation tool after a live argument-format failure.
- [x] Document the source-derived definition and units of V for model version 7.0.4. V includes substrate binding; fresh GUI readings and replay still need verification under that documented protocol.

### Required for a convincing experiment

| Priority | Owner | Deliverable | Acceptance criterion |
| --- | --- | --- | --- |
| P0 | A + B | Verify the existing web evidence | Inspect replay and match both control settings and displayed readings to the stored observations. |
| P0 | B | Define the complete measurement protocol | Agree on substrate levels, repeats, rate definition, units and comparison rule using observed timings. |
| P0 | A + B | Complete one analysis-driven follow-up | H explains why it repeats or changes a measurement, executes it within the agreed budget and links the result to the analysis. |
| P0 | A + B | Diagnose one discrepancy | A condition mismatch or failed reading triggers a relevant check; original measurements remain available. |
| P0 | B | Render the final scientific report | Show question, method, observations, checked analysis, verification, conclusion and limitations; open an evidence link successfully. |
| P0 | A + C | Rehearse incomplete outcomes | Exercise a missing capability and a budget limit without fabricated results or lost prior observations. |

### Required for the presentation

- [ ] C: prepare a short opening question and a clear explanation of the simulator's assumptions.
- [ ] C: deliver one final transcript per Gladia utterance to the existing text-input boundary.
- [ ] A + C: apply a spoken correction to the active investigation at a trial boundary and acknowledge when it takes effect.
- [ ] C: choose speech output and test brief plan, finding and blocker updates in the shared lab-colleague voice.
- [ ] A + B: enable native Screen Recording, pass the desktop check and demonstrate the matched native protocol.
- [ ] A + B: compare desktop/web completion and performance under the same protocol and budget; label unavailable results.
- [ ] All: rehearse the whole pitch twice, including Agent View and report navigation.
- [ ] C: capture a genuine backup replay, label it as a replay, and verify submission materials.

### Stretch work after rehearsal succeeds

- [ ] Add another scenario only after its controls and outputs pass a GUI interaction test.
- [ ] Add a custom model, direct Excel automation or another agent provider when the selected demo requires it.
- [ ] Build a product UI if the CLI, Agent View and Markdown viewer do not support the rehearsed presentation.

Next integration sequence: verify the recorded GUI evidence and rate units, then demonstrate the full G2 analysis/follow-up loop. The bounded comparison tool is a building block, not completion of G2. Numerical repeat counts and full-investigation budgets still need calibration.

### Teammate handoff

- A: own `selecting` and the H runner. Complete replay verification, native interaction proof and the bounded follow-up path.
- B: own `analyzing` and the scientific protocol. Confirm the rate definition/units, choose levels and repeats, and audit the scientific report.
- C: build a voice slice around Gladia final transcripts and a separate speech-output adapter. Text events should contain stable identity, transcript and run identity. Coordinate the active-run correction queue with A; it is not implemented yet.

Start with `uv sync`, then run `uv run --env-file .env jesse "Compare enzyme reaction rates at different substrate quantities" --plan-only`. Credentials and run artifacts are local and are not pushed to GitHub. Each teammate needs their own `.env`.

## Documentation for the operating agent

The controller loads the short [NetLogo guide](../src/jesse/experiments/netlogo/protocol.md) into its investigation prompt. Keep operational instructions beside that use case. Store observed UI differences and recovery steps there after a real test. Keep API documentation for developers and the project decision record in AGENT.md. A small approved catalogue and a supplied protocol are sufficient for this phase; retrieval infrastructure is outside scope.

## Checked references

- [NetLogo Enzyme Kinetics model documentation](https://ccl.northwestern.edu/netlogo/models/EnzymeKinetics): control meanings and model assumptions.
- [H desktop connection](https://hub.hcompany.ai/agents-api/your-desktop): Python desktop connection and permissions.
- [H watch and steer](https://hub.hcompany.ai/agents-api/observe-and-steer): live view, event streaming and session messages. The runner streams events through one session handle; applying live corrections remains planned.
- [Gladia partial/final transcripts](https://github.com/gladiaio/docs/blob/main/chapters/live-stt/features/partial-transcripts.mdx): finality and utterance identity for voice handoff.
