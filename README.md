# TinyOS Request-Reply Simulation

This project implements a configurable TinyOS/TOSSIM request-reply experiment
framework. It keeps the original application behavior:

- Node 1 periodically sends REQUEST packets.
- Every non-sink node in the selected scenario receives REQUEST packets and
  sends REPLY packets back.
- `analyze_log.py` reads `log.txt` and calculates overall and per-responder
  packet reception rate and average delay.

The TinyOS application is still intentionally small. The scenario files make it
easier to connect the code with the TOSSIM lab requirements and with a later WSN
system design report.

## Build

```bash
make clean
make micaz sim
```

This README documents the intended workflow. The current Codex update did not
run `make`, `make micaz sim`, `python sim.py`, `python analyze_log.py`, or any
TOSSIM simulation.

## Scenario Layout

Scenarios live under `scenarios/<name>/`. Each scenario has:

- `config.json`: node list, sink, responders, boot times, event count, and noise
  model settings.
- `topo.txt`: directed radio links in the format `src dst gain`.

Available scenarios:

- `baseline`: three-node fully connected request-reply baseline.
- `four_nodes`: adds node 4 as another responder.
- `five_nodes`: adds node 5 and uses four responders for node-scale testing.
- `multihop_chain`: keeps node 4 and node 5 away from the sink and routes
  them through relay nodes.
- `weak_link`: weakens the bidirectional link between node 1 and node 3.
- `missing_reverse_link`: keeps node 1 to node 2 reachable but removes node 2's
  direct reverse link back to node 1.

Current stage limitation: `RequestReplyC.nc` starts requests only on node 1, so
`sink` must be `1`. It also makes every non-sink node reply to requests from
node 1, so the first-stage scenarios keep `nodes` equal to `sink + responders`.

## Scenario Config

Example:

```json
{
  "nodes": [1, 2, 3],
  "sink": 1,
  "responders": [2, 3],
  "boot_times": {
    "1": 1000,
    "2": 2000,
    "3": 3000
  },
  "event_count": 30000,
  "noise": {
    "model": "constant",
    "value": -95,
    "count": 100
  }
}
```

`sim.py` also supports a future noise file or explicit noise readings through
the `noise` object, but the current scenarios use a constant noise model to
match the original script.

## Running Scenarios

After a valid TOSSIM build exists, the default scenario is `baseline`:

```bash
python sim.py
python analyze_log.py
```

Select a scenario with either a positional argument or `--scenario`:

```bash
python sim.py four_nodes
python analyze_log.py four_nodes

python sim.py five_nodes
python analyze_log.py five_nodes

python sim.py multihop_chain
python analyze_log.py multihop_chain

python sim.py --scenario weak_link
python analyze_log.py --scenario weak_link
```

Both scripts default to `log.txt`. You can choose another log path:

```bash
python sim.py baseline --log logs/baseline.txt
python analyze_log.py baseline --log logs/baseline.txt
```

## Running in a Container

The repository includes a Docker entrypoint so the project can be copied to a
fresh container and run from one command. The image is based on
`ucmercedandeslab/tinyos:tossim`, which already contains TinyOS/TOSSIM support.

From Windows PowerShell:

```powershell
.\container\run-in-container.ps1 -Scenario baseline
.\container\run-in-container.ps1 -Scenario multihop_chain -LogFile logs/multihop.txt
```

From Linux, macOS, or WSL:

```bash
sh container/run-in-container.sh baseline
sh container/run-in-container.sh multihop_chain
```

Equivalent manual Docker commands:

```bash
docker build -t tinyos-request-reply:local .
docker run --rm -v "$PWD:/app" -w /app tinyos-request-reply:local baseline
docker run --rm -v "$PWD:/app" -w /app tinyos-request-reply:local multihop_chain
```

Inside the container, `container/run-scenario.sh` runs:

```bash
make clean
make micaz sim
python sim.py <scenario> --log <log-file>
python analyze_log.py <scenario> --log <log-file>
```

The mounted project directory receives generated TinyOS/TOSSIM files and the log
file. These generated outputs are ignored by `.gitignore` and `.dockerignore`.

## Visualization UI

The visualization entry point is:

```text
ui/skeleton/index.html
```

The page is a static Tabler dashboard. It can be opened directly in a browser
without building TinyOS and without running TOSSIM:

```powershell
Start-Process .\ui\skeleton\index.html
```

Or, from Linux, macOS, or WSL:

```bash
xdg-open ui/skeleton/index.html
```

If the browser blocks local file access or you prefer a local URL, serve the
`ui` directory as static files:

```bash
python -m http.server 8080 -d ui
```

Then open:

```text
http://localhost:8080/skeleton/
```

This Python command is only a static file server. It does not run `sim.py`,
`analyze_log.py`, Docker, Make, or TOSSIM.

The visualization files are:

- `ui/skeleton/index.html`: dashboard page and layout.
- `ui/skeleton/app.js`: visualization script. It contains the current scenario
  preview data and renders the scenario list, topology SVG, route list,
  per-node table, sample dbg stream, and report evidence block.
- `ui/skeleton/styles.css`: project-specific styles layered on top of Tabler.
- `ui/vendor/tabler/`: local Tabler 1.4.0 assets and license.

The current UI uses embedded preview data. It is meant to show the experiment
structure before a real run. A later stage can connect it to a generated JSON
file from `analyze_log.py`, for example `ui/data/latest-analysis.json`.

## TOSSIM Lab Mapping

The project now maps directly to the main TOSSIM lab points:

- TOSSIM build output: `Makefile` still uses `COMPONENT=RequestReplyAppC`, so
  `make micaz sim` should produce the generated Python support files required
  by `from TOSSIM import *`.
- Python simulation control: `sim.py` creates `Tossim([])`, gets `t.radio()`,
  boots nodes with `bootAtTime()`, and advances the event queue with
  `runNextEvent()`.
- Topology file: `sim.py` loads directed links from `scenarios/<name>/topo.txt`
  instead of hard-coding a fully connected topology.
- Noise model: `sim.py` reads the configured noise settings and calls
  `addNoiseTraceReading()` and `createNoiseModel()` for each node.
- Debug channel: `RequestReplyC.nc` logs through `dbg("RequestReply", ...)`,
  and `sim.py` binds that channel to both stdout and `log.txt` with
  `addChannel()`.
- Node startup: each scenario controls per-node boot times through
  `boot_times`.
- Log analysis: `analyze_log.py` parses `SEND_REQ` and `RECV_REPLY` lines,
  then reports total PRR, end-to-end success rate, hop count, average delay,
  and per-responder statistics.

These experiments support report discussion of topology effects, asymmetric
links, node-count changes, packet reception rate, and delay. They do not yet
implement multi-hop routing, MAC protocol changes, energy modeling, or a full
WSN application design report.

## Node Scale Experiments

Use `baseline`, `four_nodes`, and `five_nodes` as a small scale-up sequence:

- `baseline` has one sink and two responders.
- `four_nodes` has one sink and three responders.
- `five_nodes` has one sink and four responders.

All node-count assumptions come from each scenario's `config.json`. The analysis
script calculates expected replies as `request_count * len(responders)` and
prints per-responder `expected`, `received`, `loss`, reception rate, average
delay, and missing `node/seq` reply pairs.

For the WSN design report, these scenarios can support a discussion of how
deployment size affects expected traffic, reply load at the sink, and packet
loss visibility. They are still single-hop teaching scenarios; a later
multi-hop routing phase is needed before using the code as evidence for a
non-direct network architecture.

## Multi-Hop Prototype

`multihop_chain` is the first non-direct topology:

- node 1 is the sink.
- node 2 and node 3 can communicate directly with node 1.
- node 4 has no direct link to node 1 and routes through node 2.
- node 5 has no direct link to node 1 and routes through node 3.

The scenario declares the intended static routes in `config.json`:

```json
"static_routes": {
  "2": 1,
  "3": 1,
  "4": 2,
  "5": 3
}
```

`sim.py` reads and validates this `static_routes` object so the experiment
metadata and terminal summary show the route plan. The TinyOS prototype mirrors
the same route table in `RequestReplyC.nc`: node 4 sends replies to node 2,
node 5 sends replies to node 3, and relays forward replies to the sink. Request
packets from the sink are forwarded by node 2 toward node 4 and by node 3
toward node 5.

The implementation logs multi-hop events with:

- `FORWARD`: a relay forwarded a request or reply.
- `DROP_DUP`: a node ignored a duplicate request or reply.
- `RECV_AT_SINK`: the sink received an end-to-end reply and recorded origin,
  last hop, sequence number, and hop count.

This is a teaching prototype for the report's network-layer section. It shows
how a static next-hop routing metric can express non-direct communication, but
it is not a full industrial routing protocol: routes are fixed, there is no
route discovery, no link-quality adaptation, and no failure recovery beyond
duplicate suppression.
