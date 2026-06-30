from __future__ import print_function

from TOSSIM import *
import argparse
import json
import os
import sys


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCENARIO_ROOT = os.path.join(BASE_DIR, "scenarios")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run a configurable TinyOS/TOSSIM request-reply scenario."
    )
    parser.add_argument(
        "scenario",
        nargs="?",
        default=None,
        help="Scenario name under scenarios/. Defaults to baseline.",
    )
    parser.add_argument(
        "--scenario",
        dest="scenario_option",
        default=None,
        help="Scenario name under scenarios/. Overrides the positional value.",
    )
    parser.add_argument(
        "--log",
        default="log.txt",
        help="Log output path. Defaults to log.txt.",
    )
    return parser.parse_args()


def load_scenario(name):
    scenario_dir = os.path.join(SCENARIO_ROOT, name)
    config_path = os.path.join(scenario_dir, "config.json")
    topo_path = os.path.join(scenario_dir, "topo.txt")

    if not os.path.isdir(scenario_dir):
        raise ValueError("Scenario directory not found: %s" % scenario_dir)
    if not os.path.isfile(config_path):
        raise ValueError("Scenario config not found: %s" % config_path)
    if not os.path.isfile(topo_path):
        raise ValueError("Scenario topology not found: %s" % topo_path)

    with open(config_path, "r") as f:
        config = json.load(f)

    config["scenario_dir"] = scenario_dir
    config["topo_path"] = topo_path
    return config


def require_node_list(config):
    nodes = [int(node_id) for node_id in config.get("nodes", [])]
    sink = int(config.get("sink", 1))
    responders = [int(node_id) for node_id in config.get("responders", [])]

    if not nodes:
        raise ValueError("Scenario config must define at least one node.")
    if sink not in nodes:
        raise ValueError("Scenario sink must be included in nodes.")
    for responder in responders:
        if responder not in nodes:
            raise ValueError("Responder %d is not included in nodes." % responder)

    if sink != 1:
        raise ValueError("Current RequestReplyC.nc starts requests only on node 1.")

    non_sink_nodes = set(nodes) - set([sink])
    if non_sink_nodes != set(responders):
        raise ValueError(
            "Current RequestReplyC.nc makes every non-sink node reply; "
            "nodes must equal sink plus responders in this stage."
        )

    return nodes, sink, responders


def load_static_routes(config, nodes, sink):
    routes = {}
    raw_routes = config.get("static_routes", {})

    for node_id, next_hop in raw_routes.items():
        node = int(node_id)
        hop = int(next_hop)

        if node not in nodes:
            raise ValueError("Static route node %d is not included in nodes." % node)
        if hop not in nodes:
            raise ValueError("Static route next hop %d is not included in nodes." % hop)
        if node == sink:
            raise ValueError("Sink node must not define a next hop to itself.")

        routes[node] = hop

    return routes


def load_topology(radio, topo_path):
    links = 0

    with open(topo_path, "r") as f:
        for line_no, raw_line in enumerate(f, 1):
            line = raw_line.split("#", 1)[0].strip()
            if not line:
                continue

            fields = line.split()
            if len(fields) != 3:
                raise ValueError(
                    "%s:%d must have: src dst gain" % (topo_path, line_no)
                )

            src = int(fields[0])
            dst = int(fields[1])
            gain = float(fields[2])
            radio.add(src, dst, gain)
            links += 1

    if links == 0:
        raise ValueError("Topology has no links: %s" % topo_path)

    return links


def load_noise_readings(config):
    noise = config.get("noise", {})

    if "readings" in noise:
        return [int(value) for value in noise["readings"]]

    if "file" in noise:
        noise_path = noise["file"]
        if not os.path.isabs(noise_path):
            noise_path = os.path.join(config["scenario_dir"], noise_path)

        readings = []
        with open(noise_path, "r") as f:
            for raw_line in f:
                line = raw_line.strip()
                if line:
                    readings.append(int(line))
        if not readings:
            raise ValueError("Noise file has no readings: %s" % noise_path)
        return readings

    value = int(noise.get("value", -95))
    count = int(noise.get("count", 100))
    return [value for _ in range(count)]


def create_noise_models(tossim, nodes, readings):
    for node_id in nodes:
        node = tossim.getNode(node_id)
        for reading in readings:
            node.addNoiseTraceReading(reading)
        node.createNoiseModel()


def boot_nodes(tossim, nodes, boot_times):
    for node_id in nodes:
        key = str(node_id)
        if key not in boot_times:
            raise ValueError("Missing boot time for node %d." % node_id)
        tossim.getNode(node_id).bootAtTime(int(boot_times[key]))


def ensure_parent_dir(path):
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)


def main():
    args = parse_args()
    scenario_name = args.scenario_option or args.scenario or "baseline"
    config = load_scenario(scenario_name)
    nodes, sink, responders = require_node_list(config)
    static_routes = load_static_routes(config, nodes, sink)

    tossim = Tossim([])
    radio = tossim.radio()

    links = load_topology(radio, config["topo_path"])
    readings = load_noise_readings(config)

    ensure_parent_dir(args.log)

    with open(args.log, "w") as log:
        tossim.addChannel("RequestReply", sys.stdout)
        tossim.addChannel("RequestReply", log)

        create_noise_models(tossim, nodes, readings)
        boot_nodes(tossim, nodes, config.get("boot_times", {}))

        event_count = int(config.get("event_count", 30000))

        print("Scenario: %s" % scenario_name)
        print("Sink node: %d" % sink)
        print("Responder nodes: %s" % ", ".join([str(x) for x in responders]))
        if static_routes:
            route_text = ", ".join(
                ["%d->%d" % (node, static_routes[node]) for node in sorted(static_routes)]
            )
            print("Static routes: %s" % route_text)
        print("Loaded topology from %s (%d links)" % (config["topo_path"], links))
        print("Noise readings per node: %d" % len(readings))
        print("Running events: %d" % event_count)

        for _ in range(event_count):
            tossim.runNextEvent()

    print("Simulation finished. Log saved to %s" % args.log)


if __name__ == "__main__":
    main()
