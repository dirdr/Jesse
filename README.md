![Jesse](jesse.png)

Jesse is a personal lab assistant. a research intern (“stagiaire”) that uses computer use to conduct experiments in web and desktop scientific software and work with Python, Excel, and the tools that you use as a researcher.

## Try it

Requires [uv](https://docs.astral.sh/uv/) and an H API key.

```sh
uv sync
cp .env.example .env  # Only if .env does not already exist.
# Set HAI_API_KEY in .env.
uv run --env-file .env jesse-netlogo --surface web --timeout 300
```

Open the printed **Agent View URL** to watch live. The current test runs NetLogo Enzyme Kinetics; evidence and reports are saved under `runs/`. See [run instructions](DESKTOP_TEST.md) for desktop setup and permissions.

To preview spoken questions through Gladia and the Pydantic AI selector without
starting H, see [live voice setup](docs/LIVE_VOICE.md).

## Architecture

Python manages sessions, budgets, records, and reports. One hosted H agent operates the selected interface. Solid arrows show implemented paths; dashed arrows show planned capabilities. Native interaction still requires permission and verification.

```mermaid
flowchart TB
    U["Researcher"]
    G["Gladia transcription<br/>Live preview"]
    P["Catalogue selector<br/>Pydantic AI"]
    T["Speech output<br/>Provider to be chosen"]

    subgraph LOCAL["Jesse - local Python application"]
        C["Controller<br/>Preflight, sessions, budgets and cancellation"]
        I["Agent context<br/>Personality and experiment protocol"]
        R["Observation recording<br/>Validation and idempotent writes"]
        A["Scientific analysis<br/>Predefined Python methods - planned"]
        F[("Investigation files<br/>Settings, readings, events and metrics")]
        O["Markdown report<br/>Outcome, limitations and evidence links"]
    end

    subgraph HAPI["H managed runtime"]
        H["One H agent<br/>Observe, reason, act and request tools"]
        W["Hosted visual browser<br/>NetLogo Web"]
        V["Agent View<br/>Live observation and replay"]
    end

    D["Local desktop connection<br/>NetLogo Desktop - permission required"]

    U -->|"Start text-driven run"| C
    U -->|"Speak a question"| G
    G -->|"Final turn: optional plan-only selection"| P
    G -.->|"Future active-run correction"| C
    I -->|"Supply behavior and protocol"| C
    C -->|"Start session and return tool results"| H
    H -->|"Stream events and request observation writes"| C
    H -->|"Operate visible controls"| W
    W -->|"Return screen observations"| H
    H -->|"Operate mouse and keyboard"| D
    D -->|"Return screenshots"| H
    C -->|"Record raw readings"| R
    R -->|"Persist validated observations"| F
    C -->|"Persist session events and metrics"| F
    C -.->|"Submit comparable measurements"| A
    A -.->|"Return results for H to choose a follow-up"| C
    C -->|"Write outcome and verification status"| O
    F -->|"Supply traceable evidence"| O
    H -->|"Expose session events"| V
    U -->|"Watch live or replay"| V
    O -->|"Present findings for review"| U
    C -.->|"Send brief progress updates"| T
    T -.->|"Speak updates"| U
```

## Example scenarios

Proposed experiments to test next; these are not selectable in the current runner.

| Scenario                | Research question                                                | Software and measurements                                                                                                                                              |
| ----------------------- | ---------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Fix city congestion     | Which traffic-light timing reduces waiting without adding roads? | [NetLogo Traffic Grid](https://ccl.northwestern.edu/netlogo/models/TrafficGrid): compare waiting time and speed at fixed traffic demand.                               |
| Investigate fire spread | How does forest density affect the spread of a fire?             | [NetLogo Fire](https://ccl.northwestern.edu/netlogo/models/Fire): vary density and repeat trials to compare the fraction burned.                                       |
| Test a new coolant      | Does this coolant absorb more heat than the reference?           | [ChemCollective coolant activity](https://chemcollective.org/activities/info/92): record masses and temperatures, calculate heat capacity, and repeat the measurement. |

Each scenario needs its own protocol and GUI interaction test. Findings describe the simulator and its assumptions.
