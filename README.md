# TinyOS Request-Reply Simulation

This project implements a simple TinyOS/TOSSIM simulation with three sensor nodes.

- Node 1 periodically sends REQUEST packets.
- Node 2 and Node 3 receive the REQUEST packets and send REPLY packets back.
- The simulation log is analyzed to calculate packet reception rate and average delay.

## Build

```bash
make clean
make micaz sim
