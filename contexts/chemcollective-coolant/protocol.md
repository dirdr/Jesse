# ChemCollective: unknown coolant

Scope: measure Compound Y solution's specific heat capacity in the simulator and compare it with the assignment's supplied ethylene glycol value. The reference is a provided constant, not a separately performed reference-coolant trial. Maximum TWO physical mixing trials, including the verification repeat; stay within the controller's time budget.

Sources:
- Activity: https://chemcollective.org/vlab/92
- Scenario: https://chemcollective.org/activities/info/92
- Assignment: https://chemcollective.org/assets/modules/activities/vlab/probs/freeze.doc

The assignment supplies ethylene glycol specific heat 2.200 J/(g·°C), Compound Y density 2.78 g/mL and water specific heat 4.184 J/(g·°C). Compound Y's specific heat is unknown. Python explicitly approximates water density as 1.00 g/mL. Findings concern the simulator under insulated mixing, negligible container heat capacity and negligible mixing enthalpy.

## Prepare

1. Operate the visible hosted browser with screenshots, clicks, drags and typing. Confirm the coolant activity and Compound Y stock. If the default lab opens, use File → Load an Assignment to find Thermochemistry / Freeze. An unavailable or blank activity is a blocker. Use visible laboratory controls for measurements; simulator scripting and hidden configuration/answer lookup are outside this investigation.
2. Call `publish_update` with a short plan: measure the unknown coolant, calculate heat capacity, then repeat with fresh samples. Use this tool for a finding, follow-up or blocker at meaningful milestones; routine clicks need no narration. Updates are shown and may be spoken in the researcher panel. Researcher messages include an event ID: use `acknowledge_researcher_message` to acknowledge it, then mark applied only after verifying the requested change. In interactive sessions answer follow-up questions using the same evidence; preserve the fixed two-trial and time limits.
3. Use a compact arrangement. Add items with the "+" button next to them in the stockroom: Compound Y and Distilled H2O (Solutions), then two Foam Cups (Glassware → Other). Every new item lands on top of the previous one at the same spot. Immediately drag each new item to its own empty area of the workbench before adding the next (the 2026-11-08 run placed the water bottle right, cup 1 centre, cup 2 lower right). Overlapping items caused accidental pours in the first pilot.
4. Transfer by dragging a stock bottle onto a separate target container. This opens a dialog titled "From <source> to <target>" with a Volume (mL) field: type the aliquot volume and click Pour, then close the dialog. This dialog exists in this HTML5 lab and was used successfully on 2026-11-08. If a drag does not open it, the items are stacked: separate them and drag again. Do not search the web or follow guides for the old Flash version (its Tools → Precise Transfer menu does not apply), and never report the transfer dialog as missing. Prepare 10 mL Compound Y in one cup and 20 mL water in the other; verify the actual volumes displayed. Keep stock and sample containers distinct.

## Establish and measure

5. After filling, select EACH sample container, use Edit → Thermal properties, enable insulation from surroundings, then set initial solution temperatures (e.g. coolant 20 °C, water 80 °C). An empty container's temperature does not establish its contents' temperature after filling. Insulate the receiving mixing vessel too; one sample cup may serve as the mixing vessel.
6. Re-read both actual solution temperatures and check they are stable BEFORE mixing. The first pilot's uninsulated hot sample cooled during setup; requested temperature values are not measurements. If readings keep changing, correct insulation before proceeding. Record remaining uncertainty explicitly.
7. Pour the full hot-water aliquot into the cooler coolant aliquot. Confirm both the transfer and final combined volume. Read the stable final temperature from the Information panel. Temperature controls establish initial conditions only; the final mixed temperature must arise from the experiment.
8. Immediately call `record_calorimetry` with actual volumes and temperatures, truthful insulation/verification flags, raw reading and screenshot/session evidence references. Require `recorded=true`. After one correction of a rejected tool call, stop if recording still fails. Python preserves the raw reading and computes only when the stated conditions pass validation.

## Verify and report

9. Use the tool's suggested follow-up for at most one additional mixing trial with fresh aliquots in clean containers. Preserve the first reading if its conditions were wrong. Recheck insulation, actual temperatures and volumes; the second trial is not reuse of the first mixture. Stop after two trials, a blocker or the execution limit.
10. Report observed conditions, supplied constants, Python results, any difference between repeat estimates and remaining uncertainty. Agreement alone does not establish statistical confidence. Drift alone does not establish a direction of bias. The unknown value is not presumed close to the reference. Compare heat absorbed per gram per degree, without claims about overall engine performance.

Current status: on 2026-11-08 the procedure above completed two insulated trials (final 46.82 °C each, c ≈ 3.724 J/(g·°C)) in about 6 minutes. A later run stacked the containers, could not open the transfer dialog and stopped on a false blocker; steps 3 and 4 now describe the working method. Replay review remains pending.
