# Jesse

Status: planning draft. Record agreed decisions here; resolve the open choices and obtain the user's final shared-understanding confirmation before implementation.

## Product

Jesse is an autonomous research technician for software-based experimental investigations. One H agent selects a suitable application from an approved catalogue, plans and executes experiments through its interface, analyzes measurements, investigates discrepancies, and produces a traceable scientific Markdown report.

An unknown experiment is an unknown sample or unanswered question within supported protocols and simulations. The agent may adapt measurements and move between supported activities. Findings describe the configured simulator and its assumptions.

## Demo scenarios and related tools

Maintain three bounded scenarios. Coolant is the preferred public-facing story; NetLogo is the first engineering test. Each simulator remains unverified until H demonstrates its required GUI interactions.

| Scenario | Researcher prompt | Tool | Evidence and completion |
| --- | --- | --- | --- |
| Test a new coolant | Can this coolant absorb more heat than the reference coolant? | ChemCollective coolant activity | Record masses, temperatures, thermal assumptions and repeat measurements; calculate specific heat capacity and compare with the supplied reference. |
| Find the production bottleneck | Does adding more ingredient always make this reaction faster? | NetLogo Desktop: Enzyme Kinetics | Hold reaction constants fixed, vary substrate quantity, record rates over consistent intervals and check for a plateau. Extend with matched inhibitor trials. |
| Investigate a sliding object | How steep must this ramp be before the object starts sliding? | Algodoo with a prepared ramp scene | Hold object and surface settings fixed, repeat angle trials, bracket the sliding threshold and compare with the friction model. |

Explain substrate as the ingredient, enzyme as the processing machine, and inhibitor as something that interferes with processing. Measure reaction rate rather than conflating final product quantity with speed. NetLogo's inhibitor model is irreversible; report that limitation. Findings concern the simulator, not a physical laboratory validation.

Choose tools by scientific fit. These are separate investigations; do not force unrelated simulators into one experimental chain. Use Python for analysis and scientific Markdown for outputs in all three scenarios.

## First implementation: NetLogo desktop feasibility

Create a repository-local Python environment and one entry point using the hosted H Agents API with a local desktop connection and HAI_API_KEY supplied through the environment. Use screen observations, mouse and keyboard; simulator scripting and headless execution are outside this test.

H opens the bundled Enzyme Kinetics model, inspects settings, sets a nonzero catalytic rate (the documented default Kr is zero), enables bounded runs, runs one experiment and reads a result. Then repeat with a different substrate quantity while keeping other settings fixed. Record settings and actual observations without requiring a predetermined numerical outcome.

Save session identifier, Agent View URL, evidence references and a short Markdown outcome in ignored run files. Limit each test session to ten minutes. Missing credentials, permissions or unreadable results produce a blocked outcome; never invent readings. macOS desktop permission prompts require user interaction.

Completion: H visibly changes a native application control, runs the simulation, reads a result and records evidence corresponding to the settings. Text input comes first; voice, automated catalogue selection and full experimental analysis follow after desktop feasibility is established.

Sources: https://ccl.northwestern.edu/netlogo/models/EnzymeKinetics ; https://chemcollective.org/activities/info/92 ; https://www.algodoo.com/what-is-it/

Retain five stories: Result Detective, Protocol Reproducer, Hands-Free Technician, Adaptive Experimenter, and Experiment Handoff. Prioritize Result Detective.

## Python and H responsibilities

Q10 accepted for the MVP: one H agent with a lightweight Python controller. Revisit this boundary only when a concrete requirement justifies a change.

Use one H reasoning and computer-use agent. A lightweight Python controller manages sessions, executes custom tools, validates records, persists state, and enforces budgets. H chooses GUI actions and follow-up experiments. H's runtime manages the observation, model, action and tool loop; the SDK executes custom tools in our application while processing the session. An additional orchestration framework is not required for the MVP.

Expose tools for inspecting the approved application catalogue, recording observations, running predefined analyses, and assembling reports. Supply bounded protocols and assumptions directly in the investigation context. RAG, vector search, corpus backfill and retrieval of earlier investigations are outside the product scope.

Operate the selected approved simulator through its browser or native desktop interface. Associate observed readings with settings, units and supporting screenshots or session events. Preserve raw measurements separately from derived results.

Use hosted H sessions and retain agent_view_url for live viewing and replay in H Agent View. Keep one backend executor for custom tools; additional observers remain read-only. The backend must remain running while tool execution is needed.

Gladia supplies voice transcription. Spoken responses require a separate speech-output implementation. Devin and Linkup are outside the MVP.

## H harness and extension boundaries

H's harness is the runtime that connects screen observations, model decisions, GUI actions and tool results. Holo is the model used by that runtime. Public documentation describes H's own runtime; it does not identify a third-party orchestration framework underlying the hosted service.

For the MVP, use the managed Agents API and its extension points: agent instructions, model selection, reasoning effort, skills, custom Python tools, browser or desktop environments, and structured output schemas. We configure this runtime rather than patch its hosted internals. Implement Jesse's experimental behavior through instructions, application selection, observation recording, analysis and report tools.

Local execution is a separate option. Client.local() runs H's supplied runtime on our machine and can use a hosted or self-hosted Holo model. Running a downloaded runtime locally does not establish that its internals are available to edit. Local mode has different capabilities from hosted sessions; verify observability and required features before changing execution mode.

For complete control of the loop, the Models API supports implementing our own observation handling, action execution, tool dispatch, memory management, retries and stopping rules. Consider this only after documenting a requirement that the managed extension points cannot satisfy.

The public HoloDesktop CLI repository now installs the CLI distributed with the hai-agents SDK. Its open-source license is not evidence that the entire hosted harness is open source. Treat client code, runtime implementation and model weights as distinct layers with their own capabilities and licenses.

## Architecture

```mermaid
flowchart TD
    U[Researcher] -->|Voice| G[Gladia]
    U -->|Text| B[Python controller]
    G -->|Transcript| B
    B -->|Instructions and tool results| H[Single H agent]
    H -->|Tool calls and findings| B
    H -->|Choose and operate| C[Approved desktop and online simulators]
    C -->|Readings and screenshots| H
    B -->|Save readings and evidence| R[Investigation files]
    B -->|Analyze measurements| P[Python analysis]
    P -->|Results and checks| B
    B --> O[Scientific Markdown artifact]
    H -.-> V[H Agent View - live and replay]
```

## Application catalogue and investigation records

Maintain a small explicit catalogue of approved tools. Each entry specifies scientific questions supported, available models or activities, launch location, browser or desktop environment, controllable parameters, observable outputs, assumptions, and tested interaction status. Candidate entries: ChemCollective, NetLogo and Algodoo. Inclusion is a proposal until its required GUI interactions have been demonstrated with H.

Select the application that supports the requested measurement and explain the choice briefly. Use another application only when it contributes a relevant experimental or analysis capability. Shared subject matter alone does not make results from different models comparable. Unsupported questions produce a blocked outcome with the missing capability identified.

Persist investigation-local settings, raw readings, units, screenshots, hypotheses, analysis and conclusions as ordinary files with stable run and step identifiers. Preserve original observations and distinguish derived values. Make retried writes idempotent. Reports link to their evidence; later investigations do not automatically retrieve or learn from these files.

## Autonomy and completion

Start each investigation with an evidence checklist and execution budget. Permit measurement repeats, configuration checks and adaptations within that budget.

Return one of three outcomes: supported conclusion, inconclusive, or blocked. Completion requires protocol-specific observations, checked units and conditions, and a verification measurement or repeat where required.

Budget exhaustion produces an inconclusive report with recorded progress. An unresolved ambiguity or unavailable required action produces a blocked result and a specific request. Ask before expanding the agreed scope or budget.

Calibrate numerical limits after the interaction feasibility exercise and settle them before implementing the full autonomous loop.

## Personality and artifacts

Conversation: a calm, concise lab colleague. Announce the next meaningful action, report material findings, and state uncertainty directly. Example: “The estimates disagree. I will check the experimental conditions before repeating the measurement.”

Reports: precise scientific language separating method, observations, analysis, interpretation and limitations.

Produce one primary Markdown artifact per investigation, with KaTeX-compatible mathematics, tables, citations and simple Mermaid TD/LR diagrams where useful. Store supporting data, plots and analysis artifacts alongside it and link the evidence. PDF and XLSX output are outside the current MVP.

The report includes the question, protocol, assumptions, observations, analysis, verification, conclusion, limitations and evidence links. Inconclusive investigations still produce reports.

Working language and speech-output approach remain open decisions.

## Construction sequence

1. Settle scope and evidence criteria. Done when the user confirms the demo question, approved application catalogue, interaction surfaces and remaining design choices.
2. Prove H interaction. Test the chosen model's controls on its actual browser or desktop surface. Done when H changes a parameter, runs the simulation, captures a result and supporting evidence, and exposes Agent View. Manually opening the application is not this proof.
3. Establish application selection and records. Done when a supported question selects a suitable catalogue entry, an unsupported question is blocked, and measurements persist with settings, units and evidence links.
4. Build a vertical experiment. Done when observed measurements reach a predefined Python analyzer and its results drive one documented follow-up experiment.
5. Add diagnosis and recovery. Done when the agent responds to a deliberate discrepancy or failed interaction, repeats a relevant measurement, and preserves original evidence within the run budget.
6. Add voice. Done when a spoken correction changes the active investigation and the selected speech output gives a brief update.
7. Produce the artifact and demo. Done when Markdown math and diagrams render in the chosen viewing surface, evidence links resolve, and supported, inconclusive and blocked outcomes have been exercised.

## Domain code: vertical slices

Organize domain code around use cases, such as selecting an application, recording an observation, analyzing measurements, or producing a report. Co-locate each slice's application logic, domain rules, input/output contracts, and relevant tests. Keep provider and persistence integrations behind narrow interfaces; share infrastructure only when multiple slices actually need it.

Build each slice end to end through its entry point, domain behavior, required integrations, persistence, and observable result before expanding to another use case. A slice is complete when its acceptance criteria are demonstrated through the real application path. Prefer a small working scientific workflow over completing horizontal technical layers separately.

## Agent working instructions

Fetch current API documentation before library or service integration. Use Context7 resolution and queries when relevant documentation is indexed; otherwise consult official documentation.

Use this file as the canonical project decision record, including its architecture diagram. AGENTS.md is the entry-point pointer to this document.

## Open decisions

- Confirm the primary demo question and the small catalogue of supported applications and models.
- Confirm a thin interaction interface with H Agent View as the execution viewer.
- Choose working language and speech-output implementation.
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
