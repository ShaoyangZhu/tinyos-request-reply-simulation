from __future__ import print_function
from TOSSIM import *
import sys

t = Tossim([])
r = t.radio()

log = open("log.txt", "w")

t.addChannel("RequestReply", sys.stdout)
t.addChannel("RequestReply", log)

nodes = [1, 2, 3]

# Build a simple fully-connected topology:
# 1 <-> 2
# 1 <-> 3
# 2 <-> 3
for src in nodes:
    for dst in nodes:
        if src != dst:
            r.add(src, dst, -50.0)

# Add a simple noise model.
for node_id in nodes:
    node = t.getNode(node_id)

    for i in range(100):
        node.addNoiseTraceReading(-95)

    node.createNoiseModel()

# Boot the three nodes at slightly different times.
t.getNode(1).bootAtTime(1000)
t.getNode(2).bootAtTime(2000)
t.getNode(3).bootAtTime(3000)

# Run the simulation.
for i in range(30000):
    t.runNextEvent()

log.close()

print("Simulation finished. Log saved to log.txt")
