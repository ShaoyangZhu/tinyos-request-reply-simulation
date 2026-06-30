# UI Design Report

## Purpose

The UI should turn the TinyOS/TOSSIM request-reply project into an experiment
workspace. The user should be able to inspect scenarios, compare topology
changes, run a selected scenario in the container workflow, read analysis
metrics, and collect report-ready evidence for the WSN design assignment.

This is not a marketing page. It should feel like a lab console: compact,
traceable, and built for repeated experiment runs.

## Target Users

- Student author: needs to run scenarios, capture evidence, and explain how the
  code supports the WSN report.
- Reviewer or instructor: needs to inspect whether scenarios match the stated
  topology and routing design.
- Future maintainer: needs to add scenarios, connect logs, and extend analysis
  without guessing how the project is organized.

## Primary Workflows

1. Select a scenario.
   The user chooses `baseline`, `four_nodes`, `five_nodes`, `weak_link`,
   `missing_reverse_link`, or `multihop_chain`.

2. Inspect scenario configuration.
   The UI shows nodes, sink, responders, event count, noise settings, and static
   routes when present.

3. Inspect topology.
   The topology panel shows directed links and marks sink, responders, and relay
   nodes. For `multihop_chain`, node 4 and node 5 must visibly have no direct
   link to sink node 1.

4. Run scenario.
   The first implementation should call the existing container workflow:
   `container/run-scenario.sh <scenario>` inside Docker. Until command execution
   is wired in, the UI skeleton should expose the intended command and a pending
   run state.

5. Read analysis output.
   The metrics section should surface request count, expected replies, received
   replies, PRR, end-to-end success rate, average delay, average hop count, and
   missing `node/seq` pairs.

6. Collect report material.
   The UI should make it easy to copy a scenario summary, metrics table, and
   topology/routing description into the WSN report draft without fabricating
   results.

## Information Architecture

- Sidebar: scenario list and quick status.
- Header: selected scenario, run state, and command actions.
- Scenario overview: config summary and route summary.
- Topology panel: node-link view and link table.
- Metrics panel: overall metrics, per-node statistics, and missing replies.
- Logs panel: recent events grouped by `SEND_REQ`, `SEND_REPLY`, `FORWARD`,
  `DROP_DUP`, and `RECV_AT_SINK`.
- Report panel: short scenario evidence text and export/copy targets.

## Screen Skeleton

### Main Experiment Console

- Left sidebar:
  - Scenario selector.
  - Scenario category labels: scale, link quality, asymmetric link, multi-hop.

- Top bar:
  - Current scenario name.
  - Run command button.
  - Analyze button.
  - Export evidence button.

- Main grid:
  - Scenario card: sink, responders, event count, noise model.
  - Route card: static routes and direct-link warnings.
  - Topology card: graph preview and link count.
  - Metrics card: PRR, delay, hop count, end-to-end success.
  - Per-node table: expected, received, loss, reception, average delay, hop.
  - Missing replies table.
  - Log stream.

## Visual Direction

- Style: dense lab dashboard, not a landing page.
- Palette: neutral background, dark text, controlled accents.
  - Blue for selected scenario and command state.
  - Green for successful delivery.
  - Amber for degraded links or missing replies.
  - Red only for errors.
- Shape: square or 6-8px radius panels. Avoid large decorative cards.
- Typography: system font stack, compact headings, tabular numbers for metrics.
- Layout: two-column workspace on desktop, stacked panels on mobile.

## Data Model

The frontend should eventually read:

- `scenarios/<name>/config.json`
  - `nodes`
  - `sink`
  - `responders`
  - `boot_times`
  - `event_count`
  - `noise`
  - `static_routes`

- `scenarios/<name>/topo.txt`
  - `src`
  - `dst`
  - `gain`

- analysis output from `analyze_log.py`
  - overall metrics
  - per-node metrics
  - missing reply pairs
  - hop counts

## Implementation Plan

1. Static skeleton.
   Create a single HTML page with sample scenario data and layout states.

2. Local file parser.
   Add a small JS parser for scenario config and topo files if the UI runs from
   a local dev server.

3. Backend command bridge.
   Add a Python or Node wrapper that can run the existing container command and
   stream output safely.

4. Analysis adapter.
   Change `analyze_log.py` to optionally emit JSON, then let the UI consume
   structured metrics instead of parsing console text.

5. Report export.
   Generate Markdown snippets for scenario evidence, topology descriptions, and
   metric tables.

## Open Questions

- Should the UI run as a static local page, a small Flask app, or a Node/Vite
  app?
- Should scenario editing be allowed in the UI, or should the first version be
  read-only?
- Should the run command use Docker only, or also support a native TinyOS
  environment?

## Recommended First Build

Build a local web app with a small Python backend:

- Backend: Flask or FastAPI.
- Frontend: static HTML/CSS/JS first, then migrate to a component framework only
  if the UI grows.
- API endpoints:
  - `GET /api/scenarios`
  - `GET /api/scenarios/<name>`
  - `POST /api/runs`
  - `GET /api/runs/<id>`
  - `GET /api/runs/<id>/analysis`

This keeps the first version close to the existing Python scripts and avoids
introducing a heavy frontend stack before the workflow is stable.
