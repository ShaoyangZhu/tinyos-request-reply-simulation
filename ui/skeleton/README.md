# UI Skeleton

This folder contains a static UI skeleton for the TinyOS/TOSSIM experiment
workspace.

Open `index.html` directly in a browser. The skeleton uses embedded sample data
and does not run TOSSIM, Docker, `sim.py`, or `analyze_log.py`.

## Files

- `index.html`: dashboard shell and screen structure.
- `styles.css`: visual system and responsive layout.
- `app.js`: sample scenario switching and placeholder metric state.

## Intended Next Step

Connect the skeleton to a small backend that reads `scenarios/`, runs the
container workflow, and exposes analysis output as JSON.
