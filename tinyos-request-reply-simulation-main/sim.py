from __future__ import print_function
from TOSSIM import *
import sys


NODES = [1, 2, 3, 4, 5, 6]
RESPONDER_NODES = [2, 3, 4, 5, 6]

# Smaller RSSI values represent weaker links. Nodes with larger IDs are placed
# farther away from node 1, so their request/reply paths are less reliable.
LINK_GAIN_TO_NODE1 = {
    2: -45.0,
    3: -55.0,
    4: -65.0,
    5: -75.0,
    6: -85.0,
}

SCENARIOS = [
    {
        "name": "low_noise",
        "description": "Six nodes, low artificial noise",
        "noise_readings": [-100, -99, -98, -97, -96],
        "event_count": 60000,
    },
    {
        "name": "medium_noise",
        "description": "Six nodes, medium artificial noise",
        "noise_readings": [-96, -94, -92, -90, -88],
        "event_count": 60000,
    },
    {
        "name": "high_noise",
        "description": "Six nodes, high artificial noise",
        "noise_readings": [-90, -88, -86, -84, -82, -80],
        "event_count": 60000,
    },
]


def link_gain(src, dst):
    if src == 1 and dst in LINK_GAIN_TO_NODE1:
        return LINK_GAIN_TO_NODE1[dst]
    if dst == 1 and src in LINK_GAIN_TO_NODE1:
        return LINK_GAIN_TO_NODE1[src]

    src_gain = LINK_GAIN_TO_NODE1.get(src, -80.0)
    dst_gain = LINK_GAIN_TO_NODE1.get(dst, -80.0)
    return min(src_gain, dst_gain) - 5.0


def add_topology(radio):
    for src in NODES:
        for dst in NODES:
            if src != dst:
                radio.add(src, dst, link_gain(src, dst))


def add_noise_model(tossim, readings):
    for node_id in NODES:
        node = tossim.getNode(node_id)

        for i in range(120):
            node.addNoiseTraceReading(readings[i % len(readings)])

        node.createNoiseModel()


def write_metadata(log, scenario):
    log.write("# SCENARIO: %s\n" % scenario["name"])
    log.write("# DESCRIPTION: %s\n" % scenario["description"])
    log.write("# NODES: %s\n" % ",".join([str(x) for x in NODES]))
    log.write("# RESPONDER_NODES: %s\n" % ",".join([str(x) for x in RESPONDER_NODES]))
    log.write("# NOISE_READINGS: %s\n" % ",".join([str(x) for x in scenario["noise_readings"]]))
    log.write("# LINK_GAIN_TO_NODE1: %s\n" % ",".join(["%d=%.1f" % (node, LINK_GAIN_TO_NODE1[node]) for node in RESPONDER_NODES]))


def run_scenario(scenario):
    log_name = "log_%s.txt" % scenario["name"]

    tossim = Tossim([])
    radio = tossim.radio()

    log = open(log_name, "w")
    write_metadata(log, scenario)

    tossim.addChannel("RequestReply", sys.stdout)
    tossim.addChannel("RequestReply", log)

    add_topology(radio)
    add_noise_model(tossim, scenario["noise_readings"])

    for node_id in NODES:
        tossim.getNode(node_id).bootAtTime(1000 * node_id)

    for i in range(scenario["event_count"]):
        tossim.runNextEvent()

    log.close()

    print("Scenario finished: %s -> %s" % (scenario["name"], log_name))


for scenario in SCENARIOS:
    run_scenario(scenario)

print("All scenarios finished.")
