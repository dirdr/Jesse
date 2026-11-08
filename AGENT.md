# Jesse

Status: research notes replaced research contexts on 2026-11-08 at the user's request. The researcher writes Markdown notes under `research/` (background, usual tools, how they like results); every investigation gives all notes to one semi-autonomous H agent, which proposes a plan, may search the web, operates only the tools in the notes unless the researcher approves another, records readings and proposes the result. The fixed catalogue, context selector, per-context protocols, `tools.py` extensions and Python outcome rules were removed. Shipped notes: mechanics (PhET Pendulum, Planet X), forest fire (NetLogo Fire, web and desktop) and thermochemistry (ChemCollective coolant). No H interaction proof exists yet for the notes-driven agent; earlier context-run proofs do not carry over.

Team constraints: three people, 24 hours until submission as of planning, with work expected to start in 8–10 hours. Plan around eight focused implementation hours.

For team task allocation and milestone handoffs, read [the hackathon work plan](docs/HACKATHON_PLAN.md) and its proposed contracts. Research areas live as notes under `research/`; the [shared agent behavior](src/jesse/instructions.md) and all notes are loaded into H's prompt. Later gates and optional multi-provider review in the work plan remain proposals; the accepted single-agent MVP still applies. This file is the canonical decision record.

## Product

Jesse is an autonomous research technician for software-based experimental investigations. A research planner selects a suitable protocol and surface from an approved catalogue. An H computer-use agent executes the experiment through its interface. The target workflow analyzes measurements, investigates discrepancies and produces a traceable scientific Markdown report.

An unknown experiment is an unknown sample or unanswered question the researcher's usual tools can address. The agent chooses the tool and method from the notes, may adapt measurements, and findings describe the tools used and their assumptions.

## Demo scenarios

Demo prompts, one per shipped note: “What is the gravity on Planet X? Measure it with the pendulum, and check whether mass changes the result.” (PhET Pendulum Lab, hidden g ≈ 14.2 m/s² checked in a headless browser); “How does tree density change how much of a forest burns? Compare 55% and 70% density and repeat both conditions.” (NetLogo Fire); “Compare this new coolant with the reference and explain which absorbs more heat per gram.” (ChemCollective coolant, reference 2.200 J/(g·°C)).

Four Fire runs cannot estimate a critical density or real wildfire risk; the notes say so, and the agent must not claim it.

New research areas are added as Markdown notes. A tool remains unverified until H demonstrates its required GUI interactions. Findings concern the tool, not a physical laboratory validation.

Sources: https://chemcollective.org/activities/info/92 ; https://chemcollective.org/vlabs ; https://ccl.northwestern.edu/netlogo/models/Fire

Retain five stories: Result Detective, Protocol Reproducer, Hands-Free Technician, Adaptive Experimenter, and Experiment Handoff. Prioritize Result Detective.

## Python and H responsibilities

Q10 was revised on 2026-11-08: keep one H computer-use operator and the lightweight Python controller, but remove catalogue selection. H reads the researcher's notes, proposes a plan with `publish_update`, waits about 20 seconds for a correction, then executes. The researcher chose: replace contexts entirely, propose-then-go autonomy, and free web search and reading while operating only tools listed in the notes unless approved.

The controller manages sessions, executes custom tools, validates records, persists state and enforces the time budget (≤ 600 s), step limit (150) and trial limit (12). H chooses tools, methods and GUI actions. H's runtime manages the observation, model, action and tool loop; the SDK executes custom tools in our application while processing the session. Browsing restrictions are instructions, not an enforced access policy.

Expose four generic tools: `publish_update`, `acknowledge_researcher_message`, `record_observation` (displayed values, units, raw text, evidence) and `analyze_readings` (linear fit of recorded values, optionally squared and through the origin, plus mean and spread). Analyses use only recorded values. RAG, vector search and retrieval of earlier investigations remain outside scope; web search happens visibly in H's browser.

Operate the chosen tool through its browser or native desktop interface. Associate observed readings with settings, units and supporting screenshots or session events. Preserve raw measurements separately from derived results.

Use hosted H sessions and retain agent_view_url for live viewing and replay in H Agent View. Keep one backend executor for custom tools; additional observers remain read-only. The backend must remain running while tool execution is needed.

Gladia supplies voice transcription. The voice workflow groups final utterances into researcher turns. Its optional preparation mode previews PydanticAI-enriched requests; plan-only mode uses the catalogue selector. The user also authorized a separate general-browser `--run` mode: each turn is enriched and submitted to one interactive H session without catalogue selection. This is not an approved experimental protocol, does not expose validated observation or analysis tools, and its scientific output remains unverified. Browser behavior restrictions are instructions rather than an enforced access policy. It does not steer an active catalogue investigation. The panel implements speech output separately; the general-browser CLI does not play spoken responses. Devin and Linkup are outside the MVP.

## H harness and extension boundaries

H's harness is the runtime that connects screen observations, model decisions, GUI actions and tool results. Holo is the model used by that runtime. Public documentation describes H's own runtime; it does not identify a third-party orchestration framework underlying the hosted service.

For the MVP, use the managed Agents API and its extension points: agent instructions, model selection, reasoning effort, skills, custom Python tools, browser or desktop environments, and structured output schemas. We configure this runtime rather than patch its hosted internals. Implement Jesse's experimental behavior through instructions, application selection, observation recording, analysis and report tools.

Local execution is a separate option. Client.local() runs H's supplied runtime on our machine and can use a hosted or self-hosted Holo model. Running a downloaded runtime locally does not establish that its internals are available to edit. Local mode has different capabilities from hosted sessions; verify observability and required features before changing execution mode.

For complete control of the loop, the Models API supports implementing our own observation handling, action execution, tool dispatch, memory management, retries and stopping rules. Consider this only after documenting a requirement that the managed extension points cannot satisfy.

The public HoloDesktop CLI repository now installs the CLI distributed with the hai-agents SDK. Its open-source license is not evidence that the entire hosted harness is open source. Treat client code, runtime implementation and model weights as distinct layers with their own capabilities and licenses.

## Architecture

Jesse has one Python controller and one hosted H computer-use operator. Python owns the notes, session lifecycle, budgets, tools, validated records and artifacts; H owns tool choice and GUI actions. Gladia supplies voice input in the local panel. The web surface starts on a search engine; the desktop surface uses the user_device bridge and is chosen at launch (`--surface desktop`).

Container deployment uses separate Nginx/React frontend and Python backend images. Nginx serves static assets and proxies HTML/API calls so Python can inject its CSRF token on the same origin. The backend uses hosted web surfaces, one replica and persistent run storage. Local native desktop control and backend microphone capture stay in the local launcher; remote browser microphone capture is a separate integration. Public deployment sets explicit allowed hosts and an HTTPS public origin. The user requested access without a login on 2026-11-08. ArgoCD manages the `jesse` namespace from the cluster repository; the existing `.env` is imported into a Kubernetes Secret, never copied into an image or committed. Every image publish from `main` bumps both chart tags in the cluster repository, so ArgoCD deploys each change automatically.

Solid connections show implemented paths; dashed connections show planned capabilities.

```mermaid
flowchart TB
    U["Researcher"]
    G["Gladia transcription"]
    T["Persona speech output<br/>Pinkman: Fish Audio<br/>Lab colleague: OpenAI"]

    subgraph LOCAL["Jesse - Python application"]
        X["Research notes<br/>research/*.md"]
        C["Controller<br/>Preflight, sessions, budgets and cancellation"]
        K["Tools<br/>Record, analyze, update, acknowledge"]
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
    X -->|"Background and usual tools"| C
    C -->|"Start session and return tool results"| H
    H -->|"Stream events and call tools"| K
    K -->|"Validated readings"| F
    H -->|"Search, read and operate tools"| W
    H -->|"Operate mouse and keyboard"| D
    C -->|"Write outcome"| O
    F -->|"Traceable evidence"| O
    F -->|"History and replay"| Y
    H -->|"Expose session events"| V
    U -->|"Watch live or replay"| V
    C -->|"Rewrite brief updates in Jesse's voice"| T
    T -->|"Speak updates"| U
```

Extensibility lives in `research/*.md` notes. Adding a research area needs only a note; no code.

The scientific loop is propose → measure → analyze → verify or adapt → propose the result. Outputs may be supported, inconclusive or blocked. The outcome is decided at the end of a run (`investigating/verdict.py`): an OpenAI model judges the recorded trials, Python analyses and the agent's report against the brief (including the researcher's notes) and returns supported_conclusion or inconclusive with a reason. Python analyses outrank agent claims, a supported conclusion must cite recorded trials, runs without measurements are blocked, and replay review remains pending. The user accepted on 2026-11-08 that this outcome is not deterministic.

Keep one operator and one custom-tool executor. Additional agent providers or a read-only reviewer remain optional future extensions. Agent View observes execution; it does not replace the controller or execute custom tools.

## Research notes and investigation records

Notes are the Markdown files under `research/` (override with `--research` or `JESSE_RESEARCH_DIR`); files starting with `_` are skipped and `research/_template.md` is the starting point. A note's title is its first `#` heading. Notes are plain text given to H; they contain no code.

`jesse "question"` runs one investigation with all notes; `--surface web|desktop` picks the surface and `--notes` lists the notes. Python checks preflight before starting H; an unavailable surface produces a blocked report. Anthropic credentials may be configured locally, but no Anthropic adapter is implemented.

Persist the brief given to H (`protocol.md`), raw readings, units, screenshots, analyses and conclusions as ordinary files under `runs/<id>/` with stable trial identifiers: `observations/` holds raw readings, `analyses/` holds derived values. Retried identical writes are idempotent; conflicting writes and readings beyond the trial limit are rejected. Reports link to their evidence. The panel sidebar lists past runs for replay; later investigations do not automatically retrieve or learn from them.

## Autonomy and completion

Session activity, report availability and scientific outcome are independent. An answer writes the report immediately. The panel opens it once per live investigation and keeps it accessible while follow-ups are possible. An idle session with a report is `report_ready`; idle without a report is `waiting` (displayed as “Session idle”). Follow-ups can resume execution and revise the report within the original limits. Session closure preserves the report and its scientific outcome. Report fetch failures remain visible and retry even after closure. An answer alone never upgrades an inconclusive scientific outcome.

Start each investigation with an evidence checklist and execution budget. Permit measurement repeats, configuration checks and adaptations within that budget.

Return one of three outcomes: supported conclusion, inconclusive, or blocked. Completion requires protocol-specific observations, checked units and conditions, and a verification measurement or repeat where required.

Budget exhaustion produces an inconclusive report with recorded progress. An unresolved ambiguity or unavailable required action produces a blocked result and a specific request. Ask before expanding the agreed scope or budget.

Calibrate numerical limits after the interaction feasibility exercise and settle them before implementing the full autonomous loop.

## Personality and artifacts

The panel offers one persona selector before an investigation. The default, Jesse Pinkman, bundles a capable, cheeky lab partner's character with the selected Fish Audio reference voice and a fixed speech model. The Lab colleague persona bundles neutral wording with OpenAI's ash voice. The registry in `src/jesse/personality.py` owns each persona's instructions, provider, model and voice. `JESSE_PERSONA` can set the initial choice (`pinkman` by default, or `plain`). The panel selection also applies to spoken questions. Each new run saves `persona.json` and passes that choice to the H worker, spoken-update writer and speech synthesizer. The choice stays fixed for that run; choose another persona before the next investigation.

Warmth and excitement follow actual findings; uncertainty and blockers get direct, serious language. Announce meaningful actions and findings in one or two natural sentences. Example: “Looks promising. Let's repeat it before we get attached.” Only propose a repeat when the protocol and budget allow it.

Reports: precise scientific language separating method, observations, analysis, interpretation and limitations.

Produce one primary Markdown artifact per investigation, with KaTeX-compatible mathematics, tables, citations and simple Mermaid TD/LR diagrams where useful. Store supporting data, plots and analysis artifacts alongside it and link the evidence. PDF and XLSX output are outside the current MVP.

The report includes the question, protocol, assumptions, observations, analysis, verification, conclusion, limitations and evidence links. Inconclusive investigations still produce reports.

Speech follows the researcher's question language. OpenAI rewrites every spoken update in the run's selected character; its assigned provider then synthesizes it. Pinkman requires both the OpenAI writer key and `FISH_API_KEY`; the lab colleague requires an OpenAI key. Missing keys, rewrite failures and synthesis failures never switch providers or speak raw status text. Legacy per-provider voice overrides are ignored; the persona is the single selection. Old runs without a saved persona use Pinkman. Audio caches include the persona, writing instructions, writer model and assigned voice. Voice milestone acceptance still requires a demonstrated spoken correction and brief spoken response.

## Construction sequence

1. Settle scope and evidence criteria. Done when the user confirms the demo question, approved application catalogue, interaction surfaces and remaining design choices.
2. Prove H interaction. Test the chosen model's controls on its actual browser or desktop surface. Done when H changes a parameter, runs the simulation, captures a result and supporting evidence, and exposes Agent View. Manually opening the application is not this proof.
3. Establish application selection and records. Done when a supported question selects a suitable catalogue entry, an unsupported question is blocked, and measurements persist with settings, units and evidence links.
4. Build a vertical experiment. Done when observed measurements reach a predefined Python analyzer and its results drive one documented follow-up experiment.
5. Add diagnosis and recovery. Done when the agent responds to a deliberate discrepancy or failed interaction, repeats a relevant measurement, and preserves original evidence within the run budget.
6. Add voice. Done when a spoken correction changes the active investigation and the selected speech output gives a brief update.
7. Produce the artifact and demo. Done when Markdown math and diagrams render in the chosen viewing surface, evidence links resolve, and supported, inconclusive and blocked outcomes have been exercised.

## Domain code: vertical slices

Use uv with pyproject.toml for Python packaging and dependency management. Keep .env.example as the credential template; load local secrets through uv run --env-file .env. Keep .env ignored. Organize each feature under src/jesse by domain/use case. Domain and application logic depend on narrow protocols; SDK and persistence adapters implement those boundaries. Compose them at the feature entry point.

Organize domain code around use cases, such as selecting an application, recording an observation, analyzing measurements, or producing a report. Co-locate each slice's application logic, domain rules, input/output contracts, and relevant tests. Keep provider and persistence integrations behind narrow interfaces; share infrastructure only when multiple slices actually need it.

Build each slice end to end through its entry point, domain behavior, required integrations, persistence, and observable result before expanding to another use case. A slice is complete when its acceptance criteria are demonstrated through the real application path. Prefer a small working scientific workflow over completing horizontal technical layers separately.

## Agent working instructions

Fetch current API documentation before library or service integration. Use Context7 resolution and queries when relevant documentation is indexed; otherwise consult official documentation.

The user authorizes regular GitHub synchronization. Commit and push tested, runnable checkpoints, report the branch and commit, and retain credentials and ignored run artifacts locally.

Use this file as the canonical project decision record, including its architecture diagram. AGENTS.md is the entry-point pointer to this document.

## Open decisions

- Confirm the primary demo question and the small catalogue of supported applications and models.
- Confirm a thin interaction interface with H Agent View as the execution viewer.
- Rehearse spoken corrections and speech output together in the live panel.
- Calibrate numerical run budgets after the feasibility exercise.
- Confirm shared understanding before implementation.

## Resources

PDF documentation is stored in docs/resources/. Coupon and credit-benefit handouts are excluded.

- Coolant activity: https://chemcollective.org/vlab/92
- Density activity: https://chemcollective.org/activities/vlab/69
- H custom tools: https://hub.hcompany.ai/agents-api/custom-tools
- H Agent View: https://hub.hcompany.ai/agents-api/observe-and-steer
- H agent configuration: https://hub.hcompany.ai/agents-api/agents/overview
- H local runtime: https://hub.hcompany.ai/agents-api/local-runtime
- H custom model loop: https://hub.hcompany.ai/models-api/build-an-agent/function-calling
- HoloDesktop CLI source: https://github.com/hcompai/holo-desktop-cli
- H setup: [getting-started guide](<docs/resources/H Company - Get Started with Agents API.pdf>)
- H references: [technical resources](docs/resources/H_Company_Agents_API_Technical_Documentation.pdf)
- Gladia references: [technical resources](docs/resources/Resources_Gladia_Technical_Documentation.pdf)
- Linkup references, outside the current MVP: [technical resources](docs/resources/Resources_Linkup_Technical_Documentation.pdf)
