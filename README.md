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

## Running on a Linux VM Without Docker

If the project is copied to a Linux virtual machine with TinyOS/TOSSIM already
installed, run the simulation from the repository root. Do not start from
`ui/skeleton/index.html`; that page is only a visualization preview.

First make sure the TinyOS environment is loaded in the shell. The exact command
depends on the VM image, but a working shell should provide `make`, `tos-make`,
and the TinyOS environment variables such as `TOSROOT` and `MAKERULES`.

Then build the TOSSIM Python support files:

```bash
make clean
make micaz sim
```

Run one scenario and analyze its log:

```bash
python sim.py baseline --log log.txt
python analyze_log.py baseline --log log.txt
```

Run the multi-hop scenario:

```bash
python sim.py multihop_chain --log logs/multihop_chain.txt
python analyze_log.py multihop_chain --log logs/multihop_chain.txt
```

The native Linux VM workflow is:

```text
make micaz sim -> python sim.py <scenario> -> python analyze_log.py <scenario>
```

The visualization UI is separate. Opening `ui/skeleton/index.html` or running
`python -m http.server 8080 -d ui` only displays static UI files. It does not
start TOSSIM, does not execute `sim.py`, and does not refresh from `log.txt`.
To control simulation from the browser, use `./ui/run-ui.sh` as described in
the Visualization UI section.

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

The UI has two modes.

### Interactive runner mode

Use this mode on a Linux VM when you want the browser button to start the native
TinyOS/TOSSIM workflow. The shell must already have the TinyOS environment
loaded.

From the repository root:

```bash
chmod +x ui/run-ui.sh
./ui/run-ui.sh
```

Then open:

```text
http://127.0.0.1:8080/skeleton/
```

If the VM needs Python 2 for the generated TOSSIM module, keep the UI server on
Python 3 but run the simulation scripts with Python 2:

```bash
TOSSIM_PYTHON=python2 ./ui/run-ui.sh
```

For older TinyOS VM images where `python3` is Python 3.4, use the same command
shape. The UI server avoids Python 3.5-only APIs:

```bash
PYTHON_BIN=python3 TOSSIM_PYTHON=python ./ui/run-ui.sh
```

The UI button calls `POST /api/run`. The local server then runs:

```text
make clean
make micaz sim
python sim.py <scenario> --log logs/<scenario>.txt
python analyze_log.py <scenario> --log logs/<scenario>.txt --json-out ui/results/<scenario>.json
```

The UI polls `GET /api/status` while the command is running and loads
`GET /api/results?scenario=<scenario>` after analysis completes. Real output is
written to:

- `logs/<scenario>.txt`: TOSSIM debug log.
- `ui/results/<scenario>.json`: analysis data used by the UI.
- `ui/results/<scenario>.runner.log`: backend command output.

`ui/results/` is ignored by Git except for its local ignore file.

Optional server settings:

```bash
HOST=0.0.0.0 PORT=8080 ./ui/run-ui.sh
PYTHON_BIN=python3 TOSSIM_PYTHON=python2 ./ui/run-ui.sh
```

### Remote Linux VM access

If the UI runner is started on a remote Linux VM and you want to open it from
your local browser, use one of these two options.

Option 1: listen on the VM network interface and open the VM IP directly:

```bash
git checkout codex/tossim-followup
chmod +x ui/run-ui.sh
HOST=0.0.0.0 PORT=8080 ./ui/run-ui.sh
```

Then open this URL from your local machine:

```text
http://<remote-vm-ip>:8080/skeleton/
```

If the VM requires Python 2 for TOSSIM:

```bash
HOST=0.0.0.0 PORT=8080 TOSSIM_PYTHON=python2 ./ui/run-ui.sh
```

The VM firewall or cloud security group must allow inbound TCP traffic on port
`8080`.

Option 2: keep the server bound to localhost and use SSH port forwarding:

```bash
ssh -L 8080:127.0.0.1:8080 user@<remote-vm-ip>
```

In the SSH session on the remote VM:

```bash
git checkout codex/tossim-followup
chmod +x ui/run-ui.sh
./ui/run-ui.sh
```

Then open this URL on your local machine:

```text
http://127.0.0.1:8080/skeleton/
```

Use the SSH tunnel option when the remote firewall does not expose port `8080`
or when you do not want the UI runner reachable by other machines.

### Static preview mode

You can still open the page as static files:

```powershell
Start-Process .\ui\skeleton\index.html
```

or:

```bash
python -m http.server 8080 -d ui
```

Static mode only displays the page and embedded preview data. It does not run
Make, TOSSIM, `sim.py`, or `analyze_log.py`, and the Run button cannot start a
simulation unless the page is served by `ui/server.py`.

The visualization files are:

- `ui/skeleton/index.html`: dashboard page and layout.
- `ui/skeleton/app.js`: visualization script. It renders preview data, calls the
  local runner API, polls status, and refreshes metrics from JSON output.
- `ui/skeleton/styles.css`: project-specific styles layered on top of Tabler.
- `ui/server.py`: local HTTP server and native TinyOS/TOSSIM command runner.
- `ui/run-ui.sh`: Linux VM startup script for the interactive UI runner.
- `ui/vendor/tabler/`: local Tabler 1.4.0 assets and license.

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
