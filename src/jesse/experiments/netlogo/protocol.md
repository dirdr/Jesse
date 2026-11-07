# NetLogo interaction feasibility guide

Purpose: prove GUI operation and readable evidence in two trials. This is not the full bottleneck investigation. Use the selected desktop or web surface specified in the run instructions. Use no shell, Command Center, JavaScript execution, model code changes, headless simulation or alternative surface.

## Procedure

1. On desktop, open NetLogo and locate Enzyme Kinetics in File → Models Library → Sample Models → Chemistry & Physics → Chemical Reactions. On web, wait for the supplied model URL to load. Confirm the visible model title. If controls differ, inspect the interface visually.
2. Inspect visible controls and outputs. Record installed version if available, initial settings and evidence. Set Kr above zero; its documented default is zero. Keep Kc, Kd and Kr fixed across trials.
3. Enable PAUSE?; it bounds a run at 30 ticks. Choose and record a VOLUME setting, which controls substrate quantity. Run SETUP, then GO, then RECORD V once stopped.
4. Capture the actual output, interval, settings and supporting screenshot/session reference. Verify that the output is a rate rather than final product quantity. Use visible plot inspection if available; if an exact rate is unreadable, preserve the evidence and report the blocker.
5. Change VOLUME to a distinct setting. Repeat SETUP, GO and RECORD V with the same reaction constants and pause setting. Record this as a separate trial.
6. Call analyze_measurements to check comparability and compute the rate difference. Use its calculations in the report. If it reports mismatched conditions, explain the issue without asserting a scientific trend. Describe suggested repeats as future work; the feasibility test remains bounded to two trials.

Completion requires evidence for both trials, at least one visible parameter change, simulation execution and readable numerical results matched to their settings. Stop after two trials or on a blocker; the controller enforces a ten-minute session limit.

## Evidence and recovery

- Associate each reading with a trial identifier, control settings, displayed units, tick interval and evidence reference. Unknown units remain unknown; report simulator units as shown.
- Record observations before interpreting them. Never supply an expected number as a reading or invent an evidence reference.
- Call record_observation after each reading, including unreadable results, before proceeding. Use separate stable observation/trial IDs and include VOLUME, Kc, Kd, Kr, PAUSE?, raw output, interval and actual evidence references. Unknown fields remain null. The controller supplies the recording timestamp and run identity; do not invent them.
- After an ambiguous click, inspect the screen and verify the control before continuing. A permission dialog, missing model or unreadable output produces a blocked outcome with the exact missing capability. macOS permission prompts require the human operator.
- Preserve completed observations if the budget expires; return inconclusive with the progress achieved.

## Outcome

Return a short scientific Markdown report: method, trial table, comparison, limitations, evidence and outcome. Use supported conclusion only for the narrow interaction test when all completion criteria hold. Distinguish success of GUI navigation from scientific support for saturation. Session ID and Agent View URL should be retained by the controller; cite available session events without fabricating local screenshots.

## Model assumptions

The inhibitor mechanism is irreversible. Findings describe this simulator; retain that limitation for later inhibitor experiments.

Source: [official Enzyme Kinetics documentation](https://ccl.northwestern.edu/netlogo/models/EnzymeKinetics). Verify control availability on the installed version during the test. Guide prepared 2026-11-07; actual H interaction remains unverified.
