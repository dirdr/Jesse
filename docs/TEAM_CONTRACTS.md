# Proposed team contracts

Status: partial implementation. Catalogue selection, raw observation recording and bounded NetLogo rate analysis are implemented. The researcher-event/correction boundary and full report contract remain proposed. Owner A coordinates changes with the affected owners before integration. Use ordinary Python values and JSON files; no message broker is needed.

## Experiment definition

Each approved investigation supplies `experiment_id`, `supported_questions`, `application`, `environment`, `launch_location`, `protocol`, `settings_schema`, `measurement_schema`, `assumptions`, `analysis_method`, `completion_criteria` and `interaction_status` (`unverified`, `verified` or `blocked`, with evidence).

Start with one explicit NetLogo entry. Selection returns its ID and a brief scientific reason, or a blocked result for unsupported questions. A future coolant definition supplies its own units and analyzer through the same boundary. Reuse the controller and observation envelope; keep model-specific science in its slice. Registration is a proposal until GUI evidence establishes the required interactions.

Current selection output: `status` (`ready` or `blocked`), original `question`, `reason`, `experiment_id`, `surface` and `maximum_trials`. Only the question and surface preference come from the researcher. The model proposes a registered ID and available surface; Python supplies the fixed trial limit and validates the selection. The initial catalogue/selector implementation is in `src/jesse/selecting`.

## Researcher input: voice or text → controller

Fields: `event_id`, `run_id` (null for a new investigation), `source` (`text` or `voice`), `text`, `received_at` (UTC), `utterance_id` (voice only).

For Gladia, dispatch only final transcripts to the controller. Use provider utterance identity to deduplicate delivery; partial text updates the display only. Gladia marks transcript finality using `data.is_final` and shares `data.id` across updates to an utterance. [Provider reference](https://github.com/gladiaio/docs/blob/main/chapters/live-stt/features/partial-transcripts.mdx).

The controller returns `accepted`, `queued` or `rejected`, with a reason and the linked run. Acknowledgement means the input was received; record a separate event when the agent applies the correction. Apply changes at a trial boundary and mark an interrupted trial incomplete. A correction within scope uses the same active investigation; broader scope still requires agreement.

## Observation: agent/controller → records and analysis

Required fields:

| Field | Meaning |
| --- | --- |
| `run_id`, `trial_id`, `observation_id` | Stable identifiers; retries reuse the same observation ID. |
| `observed_at` | UTC timestamp. |
| `application`, `model`, `version` | Actual tool/model identity; version can be unknown with explanation. |
| `settings` | Observed control labels and values, including varied and fixed parameters. |
| `interval` | Start/end ticks or other observed interval, with unit; unknown fields remain null. |
| `quantity`, `value`, `unit` | Read quantity and numeric value. Unreadable values remain null with a reason. Preserve simulator units; never assign physical units by inference. |
| `raw_reading` | Original displayed text or description of the observed plot reading. |
| `evidence` | Nonempty list of screenshot paths or session/event references, with session ID where relevant. |
| `status`, `reason` | `observed`, `unreadable` or `interrupted`; explain incomplete records. |

Save raw observations before analysis. Identical writes with the same ID are idempotent; conflicting values for that ID are rejected. Corrections create a new observation referencing the original, rather than overwriting it. Analysis excludes incomplete readings and reports exclusions.

## Analysis: analyzer → controller and report

Fields: `analysis_id`, `input_observation_ids`, `method`, `derived_values`, `comparison`, `limitations`, `suggested_follow_up` (nullable, with reason and requested conditions).

Use predefined Python analyses with validated inputs. Store the method, units and input IDs with each derived value. Check comparable conditions and intervals before comparing rates. Establish thresholds after the feasibility test; no guessed plateau threshold is part of this contract. H chooses whether and how to perform the suggested follow-up within the remaining budget.

## Report: controller → renderer

Fields: `run_id`, `question`, `protocol`, `assumptions`, `observations`, `analyses`, `verification`, `outcome`, `conclusion`, `limitations`, `evidence`.

`outcome` is `supported_conclusion`, `inconclusive` or `blocked`. The renderer creates Markdown for all three. Report statements cite observation or analysis IDs; evidence links must resolve for the audience's viewing environment. Session completion is execution metadata, not a scientific conclusion.

Each owner supplies a clearly labelled synthetic fixture for their output and demonstrates that the next consumer can read it. Synthetic fixtures belong in tests or examples and must never be presented as experiment findings.
