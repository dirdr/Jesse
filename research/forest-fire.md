# Forest fire spread

## Background

I study how fire spreads through a forest as a percolation process. Tree density is the main control: below a threshold fires stay local, above it they cross the forest. Each run starts from a new random forest, so results vary between runs and need repeats.

## Usual tools

- **NetLogo Fire model (web)**: https://www.netlogoweb.org/launch#https://www.netlogoweb.org/assets/modelslib/Sample%20Models/Earth%20Science/Fire.nlogox
  Set the `density` slider, click `setup` (always after changing density), then `go`. Wait until the fire stops and read `percent burned`. Ticks are model steps, not seconds. Moving the speed slider right only makes it faster to watch.
- **NetLogo desktop**: `/Applications/NetLogo 7.0.4/NetLogo 7.0.4.app`, Models Library → Sample Models → Earth Science → Fire. Same controls.

## How I like results

Percent burned for each density, with at least two fresh forests per density. Report means and ranges. Do not claim a critical threshold from a handful of runs.
