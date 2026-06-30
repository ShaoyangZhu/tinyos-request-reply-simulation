# UI Skeleton

This folder contains a static Tabler-based UI shell for the TinyOS/TOSSIM
experiment workspace.

The page can be opened as a static preview, but the Run button only starts a
simulation when the page is served by `../server.py`.

## How to Run

### Interactive runner mode

Use this on a Linux VM with TinyOS/TOSSIM already installed and loaded in the
shell:

```bash
chmod +x ui/run-ui.sh
./ui/run-ui.sh
```

Then open:

```text
http://127.0.0.1:8080/skeleton/
```

If the generated TOSSIM Python module requires Python 2:

```bash
TOSSIM_PYTHON=python2 ./ui/run-ui.sh
```

Clicking `Run simulation` sends `POST /api/run` to the local server. The server
runs:

```text
make clean
make micaz sim
python sim.py <scenario> --log logs/<scenario>.txt
python analyze_log.py <scenario> --log logs/<scenario>.txt --json-out ui/results/<scenario>.json
```

The UI polls `/api/status` and refreshes from
`/api/results?scenario=<scenario>` after analysis completes.

### Remote Linux VM access

If the runner is on a remote VM and your browser is on your local machine, either
bind the runner to the VM network interface:

```bash
git checkout codex/tossim-followup
chmod +x ui/run-ui.sh
HOST=0.0.0.0 PORT=8080 ./ui/run-ui.sh
```

Then open:

```text
http://<remote-vm-ip>:8080/skeleton/
```

If TOSSIM needs Python 2:

```bash
HOST=0.0.0.0 PORT=8080 TOSSIM_PYTHON=python2 ./ui/run-ui.sh
```

Or keep the runner private and use SSH port forwarding:

```bash
ssh -L 8080:127.0.0.1:8080 user@<remote-vm-ip>
```

In that SSH session, run:

```bash
git checkout codex/tossim-followup
chmod +x ui/run-ui.sh
./ui/run-ui.sh
```

Then open this URL on your local machine:

```text
http://127.0.0.1:8080/skeleton/
```

### Static preview mode

From the repository root on Windows PowerShell:

```powershell
Start-Process .\ui\skeleton\index.html
```

From Linux, macOS, or WSL:

```bash
xdg-open ui/skeleton/index.html
```

If direct `file://` access is inconvenient, serve the `ui` directory as static
files:

```bash
python -m http.server 8080 -d ui
```

Then open:

```text
http://localhost:8080/skeleton/
```

The HTTP server command only serves static UI files. It does not run TinyOS,
TOSSIM, `sim.py`, `analyze_log.py`, Docker, or Make.

## Files

- `index.html`: Tabler dashboard shell and screen structure.
- `styles.css`: project-specific styles for topology, logs, and experiment
  markers.
- `app.js`: scenario switching, topology rendering, runner API calls, status
  polling, JSON result loading, and copy actions.
- `../server.py`: local HTTP server and native simulation runner.
- `../run-ui.sh`: Linux VM startup script for the interactive runner mode.
- `../results/`: generated JSON analysis files and runner logs.
- `../vendor/tabler/`: local Tabler 1.4.0 assets.

## UI Mapping

- Scenario navigation maps to the `scenarios/` folders.
- The topology panel maps to each scenario's `topo.txt`.
- The static route list maps to `static_routes` in `config.json`.
- Metric and table panels load JSON written by `analyze_log.py --json-out` when
  a result exists.
- Debug stream and report evidence blocks show the log fields expected by the
  analysis workflow.

## Remaining Work

The current runner executes one scenario at a time and keeps only local JSON
files. A later version can add run history, compare two scenarios side by side,
or stream raw `log.txt` lines while TOSSIM is still running.
