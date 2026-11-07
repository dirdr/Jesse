# Forest density and fire spread

Question: how does initial tree density change the final percentage of trees burned in NetLogo's bundled Fire model?

Operate the visible interface using mouse and keyboard. Use the selected surface throughout. Complete at most four fresh simulations within the original run budget, in this order: `low-1` (55%), `high-1` (70%), `low-2` (55%), `high-2` (70%). Keep model code and world settings unchanged. Use the fresh second pair to check whether the first comparison repeats; never promise a particular result.

## Open the model

1. Publish a short plan using `publish_update`: compare a sparse and a denser forest, then repeat both with newly generated forests.
2. Desktop: open NetLogo at the supplied app path, then File → Models Library (Cmd+D) → Sample Models → Earth Science → Fire. If necessary, use File → Open (Cmd+O), then the macOS Go to Folder dialog (Cmd+Shift+G) to open `/Applications/NetLogo 7.0.4/models/Sample Models/Earth Science/Fire.nlogox`. Wait until the window title says Fire and the Interface tab shows `density`, `setup`, `go`, `percent burned` and the forest view. Close a startup welcome dialog if it obscures the model.
3. Web: the supplied link should open Fire. If it opens a different model, use Search the Models Library to choose Fire under Earth Science. Wait for the same controls to appear; an unavailable or incompatible model is a blocker. Do not silently change surfaces.

## Measure each trial

4. Confirm Go is stopped. Set the density to the required value and read it back. Desktop: right-click the density slider, choose Edit and set its current Value (leave its minimum, maximum and increment unchanged), then confirm. Web: use the slider's numeric value if editable; otherwise adjust the slider and read back the exact value. Do not enter simulator commands to set values or run trials.
5. Click Setup **after** changing density. Density changes take effect only on the next Setup. Confirm the visible forest resets, ticks reads zero and percent burned reads zero. Capture evidence of the density and fresh forest. For repeats, click Setup again even when the density is unchanged.
6. Click Go once. Watch the red fire spread. You may move the speed slider moderately right if needed to finish within budget; speed affects presentation, not model ticks. Preserve at least one visible propagation frame. Keep the same speed thereafter.
7. Wait until Go stops naturally, the fire and fading embers disappear, and ticks and percent burned stop changing. A paused simulation with red fire still visible is incomplete. Capture a final screenshot showing density, ticks, percent burned and the forest.
8. Immediately call `record_fire_trial` with the stable trial ID, displayed `density_percent`, `percent_burned` and `ticks`, plus `fresh_setup`, `completed`, `settings_verified`, the verbatim `raw_reading` and evidence references for setup and completion. If a value is unreadable, pass null and explain it in `raw_reading`; use false for an unverified condition. Require `recorded=true` before resetting anything. Preserve failed or interrupted trials under their original IDs; the four-trial cap includes them.
9. After `high-1`, use the returned analysis to publish the initial difference and explain why the fresh second pair is needed. After `high-2`, publish the repeated comparison, including any disagreement. If budget is short, save current evidence and report the missing repeats rather than adding trials or fabricating readings.

## Report

10. Write the question, GUI method, actual trial table, mean and range at each density, and the high-minus-low difference in **percentage points** from the checked analysis. Describe agreement or disagreement of the two pairs. Treat ticks as model steps. Separate your interpretation from raw observations and retain source and replay links.
11. Explain that each Setup generates a random forest; four runs cannot locate a critical threshold or estimate a crossing probability. The model has no wind, moisture or firefighting and spreads only to four neighbors. A visually striking result remains a simulator result pending replay review. If all evidence is recorded, answer with the report; follow-ups remain within the existing trial and time limits.

Measurement definition checked against the bundled NetLogo 7.0.4 Fire model: `percent burned = 100 × burned-trees / initial-trees`. The initial count is the green trees after igniting the left boundary. Record the displayed percentage, not the fraction of the whole grid that appears black.

Sources: [Fire model and citation: Wilensky (1997)](https://ccl.northwestern.edu/netlogo/models/Fire), [NetLogo Web capabilities](https://www.netlogoweb.org/docs/faq).
