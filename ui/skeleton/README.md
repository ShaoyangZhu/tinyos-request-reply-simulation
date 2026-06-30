# UI Skeleton

This folder contains a static Tabler-based UI shell for the TinyOS/TOSSIM
experiment workspace.

Open `index.html` directly in a browser. The page uses embedded scenario preview
data and does not run TOSSIM, Docker, `sim.py`, or `analyze_log.py`.

## Files

- `index.html`: Tabler dashboard shell and screen structure.
- `styles.css`: project-specific styles for topology, logs, and experiment
  markers.
- `app.js`: scenario switching, topology rendering, placeholder metrics, and
  copy actions.
- `../vendor/tabler/`: local Tabler 1.4.0 assets.

## UI Mapping

- Scenario navigation maps to the `scenarios/` folders.
- The topology panel maps to each scenario's `topo.txt`.
- The static route list maps to `static_routes` in `config.json`.
- Metric and table panels are placeholders for future `analyze_log.py` output.
- Debug stream and report evidence blocks show the log fields expected by the
  analysis workflow.

## Intended Next Step

Add a small JSON handoff file, for example `ui/data/latest-analysis.json`,
written by a future wrapper around `analyze_log.py`. The UI can then replace the
current preview values without starting TOSSIM from the browser.
