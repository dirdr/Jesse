# Meaning of the Velocity reading

Verified against the linked NetLogo Web Enzyme Kinetics asset, model version 7.0.4.

The model computes `V = (substrate_added - free_substrate_count) / ticks_at_calculation`. Its units are **substrate molecules/model tick**, derived from the model definition rather than a visible unit label. Keep the displayed number unchanged in raw_reading.

This is a free-substrate depletion proxy. Bound substrate contributes to the numerator as well as substrate converted into product. V is not an instantaneous product-formation rate. Complex formation can contribute even when Kr is zero; this protocol still requires nonzero Kr to permit catalysis.

The model calculates V before incrementing its tick counter. At the pause display of 30 ticks, the last calculation uses denominator 29. Read the displayed V rather than recomputing it as product count divided by 30. Compare only matched runs stopped at the same displayed interval.

For this supplied web asset, record quantity as reaction velocity (V), unit as substrate molecules/model tick, and state this definition and limitation in the report. For another model version, confirm the definition before assigning units. Two readings cannot establish saturation or statistical significance.

Source: [official model asset](https://www.netlogoweb.org/assets/modelslib/Sample%20Models/Chemistry%20%26%20Physics/Chemical%20Reactions/Enzyme%20Kinetics.nlogox), procedures calculate-velocity and go. Inspection defines the protocol; all experimental readings must still come from the GUI.
