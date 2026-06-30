# TinyOS Request-Reply Simulation

This project implements a TinyOS/TOSSIM request-reply simulation with six sensor nodes.

- Node 1 periodically sends REQUEST packets.
- Node 2 through Node 6 receive the REQUEST packets and send REPLY packets back.
- The simulation runs multiple artificial-noise scenarios.
- Link quality is different for each responder node to simulate distance from node 1.
- The simulation logs are analyzed to calculate packet reception rate and average delay.

## Build

```bash
make clean
make micaz sim
```

## Run

```bash
python sim.py
python analyze_log.py log_low_noise.txt log_medium_noise.txt log_high_noise.txt
```

`sim.py` writes three simulation logs:

- `log_low_noise.txt`
- `log_medium_noise.txt`
- `log_high_noise.txt`

`analyze_log.py` prints the packet statistics, generates one report for each log,
and creates `comparison_report.html` when multiple logs are analyzed together.

Each scenario is run in a separate Python process so TOSSIM starts from a clean
simulation state. You can also run one scenario at a time:

```bash
python sim.py low_noise
python sim.py medium_noise
python sim.py high_noise
```

## Visualization

Open the generated comparison report in a browser:

```bash
firefox comparison_report.html
```
