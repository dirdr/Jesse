# Hidden gravity on Planet X

Question: what is the gravitational acceleration on Planet X? The simulator hides it. Recover it from pendulum periods, then check what does and does not affect the measurement.

Operate the visible PhET interface with the mouse. Never read gravity from code, URLs or developer tools. At most six trials, in this order: `fit-1`, `fit-2`, `fit-3`, `fit-4`, then the `mass` control, then the optional `amplitude` control.

## Set up once

1. Publish a short plan with `publish_update`: measure periods at four lengths on Planet X, fit T² against L, then run a mass control.
2. The Lab screen opens with Length 1, Mass 1 and Gravity panels on the right. Open the Gravity dropdown (it shows "Earth") and choose **Planet X**. The panel then shows "What is the value of gravity?" and hides the number.
3. Keep Friction at **None** (slider fully left).
4. Tick **Period Timer** in the bottom-left box. A yellow Period panel appears with a ▷ button and a readout in seconds.

## Measure each fit trial

5. Set the length. Drag the Length 1 slider thumb near the target, then use the ◀ ▶ arrows (0.01 m per click) only if needed. Targets: `fit-1` ≈ 0.30 m, `fit-2` ≈ 0.50 m, `fit-3` ≈ 0.70 m, `fit-4` ≈ 0.95 m. Exact targets are not required; record the displayed value.
6. Keep Mass 1 at 1.00 kg.
7. Drag the blue bob a short way sideways so it swings at about 5–10°. Use the protractor ticks to estimate the angle. Release it; it swings on its own.
8. Click the Period Timer's ▷ button and wait for one full swing until a non-zero period appears, such as `1.3967 s`.
9. Capture a screenshot showing the length readout, mass readout and period readout.
10. Immediately call `record_pendulum_trial` with the trial ID, the displayed `length_m`, `mass_kg`, your `angle_deg` estimate, the displayed `period_s`, `planet_x` and `friction_none` flags, the verbatim `raw_reading` and evidence references. Require `recorded=true` before changing anything.

## Controls

11. `mass`: keep the `fit-4` length, set Mass 1 to about 0.20 kg, swing at 5–10°, measure and record. Mass should not change the period.
12. `amplitude` (only if time allows): keep the `fit-4` length and mass 1.00 kg, drag the bob to about 60°, measure and record.

After `fit-2`, publish the first estimate returned by the tool. After the controls, publish the checked result.

## Report

13. Answer with the gravity estimate and fit quality returned by the tool, the mass check and, if measured, the amplitude check. Separate observations from interpretation. The Python analysis decides the outcome; do not claim more than it supports.

Sources: [PhET Pendulum Lab](https://phet.colorado.edu/en/simulations/pendulum-lab), [teacher guide](https://phet.colorado.edu/files/teachers-guide/pendulum-lab-html-guide_en.pdf).
