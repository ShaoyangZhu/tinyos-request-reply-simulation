from __future__ import print_function

import argparse
import datetime
import json
import os
import re


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCENARIO_ROOT = os.path.join(BASE_DIR, "scenarios")

SEND_REQ_PATTERN = re.compile(r"SEND_REQ node=(\d+) seq=(\d+) time=(\d+)")
RECV_REPLY_PATTERN = re.compile(
    r"RECV_REPLY node=(\d+) from=(\d+) seq=(\d+) time=(\d+)(?:.*hop_count=(\d+))?"
)
RECV_AT_SINK_PATTERN = re.compile(
    r"RECV_AT_SINK node=(\d+) origin=(\d+) from=(\d+) seq=(\d+) hop_count=(\d+) time=(\d+)"
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Analyze a request-reply TOSSIM log for one scenario."
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
        help="Log file path. Defaults to log.txt.",
    )
    parser.add_argument(
        "--json-out",
        default=None,
        help="Optional JSON output path for the visualization UI.",
    )
    return parser.parse_args()


def load_config(name):
    config_path = os.path.join(SCENARIO_ROOT, name, "config.json")
    if not os.path.isfile(config_path):
        raise ValueError("Scenario config not found: %s" % config_path)

    with open(config_path, "r") as f:
        return json.load(f)


def average(values):
    if values:
        return sum(values) / float(len(values))
    return 0.0


def percent(numerator, denominator):
    if denominator:
        return 100.0 * float(numerator) / float(denominator)
    return 0.0


def ensure_parent_dir(path):
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)


def record_sink_receive(
    sink,
    responders,
    send_times,
    received_replies,
    delays_by_responder,
    hop_counts_by_responder,
    node,
    origin,
    seq,
    recv_time,
    hop_count,
):
    if node != sink or origin not in responders:
        return

    key = (origin, seq)
    if key in received_replies:
        return

    received_replies.add(key)

    if seq in send_times:
        delays_by_responder[origin].append(recv_time - send_times[seq])

    if hop_count is not None:
        hop_counts_by_responder[origin].append(hop_count)


def analyze_log(log_path, sink, responders):
    send_times = {}
    received_replies = set()
    delays_by_responder = {}
    hop_counts_by_responder = {}

    for responder in responders:
        delays_by_responder[responder] = []
        hop_counts_by_responder[responder] = []

    with open(log_path, "r") as f:
        for line in f:
            m = SEND_REQ_PATTERN.search(line)
            if m:
                node = int(m.group(1))
                seq = int(m.group(2))
                send_time = int(m.group(3))

                if node == sink:
                    send_times[seq] = send_time

            m = RECV_AT_SINK_PATTERN.search(line)
            if m:
                record_sink_receive(
                    sink,
                    responders,
                    send_times,
                    received_replies,
                    delays_by_responder,
                    hop_counts_by_responder,
                    int(m.group(1)),
                    int(m.group(2)),
                    int(m.group(4)),
                    int(m.group(6)),
                    int(m.group(5)),
                )

            m = RECV_REPLY_PATTERN.search(line)
            if m:
                node = int(m.group(1))
                origin = int(m.group(2))
                seq = int(m.group(3))
                recv_time = int(m.group(4))
                hop_count = int(m.group(5)) if m.group(5) is not None else None

                record_sink_receive(
                    sink,
                    responders,
                    send_times,
                    received_replies,
                    delays_by_responder,
                    hop_counts_by_responder,
                    node,
                    origin,
                    seq,
                    recv_time,
                    hop_count,
                )

    request_count = len(send_times)
    expected_reply_count = request_count * len(responders)
    actual_reply_count = len(received_replies)
    expected_replies = set()

    for seq in send_times:
        for responder in responders:
            expected_replies.add((responder, seq))

    missing_replies = sorted(
        expected_replies - received_replies,
        key=lambda item: (item[1], item[0]),
    )

    return {
        "request_count": request_count,
        "expected_reply_count": expected_reply_count,
        "actual_reply_count": actual_reply_count,
        "packet_reception_rate": percent(actual_reply_count, expected_reply_count),
        "average_delay": average(
            [delay for delays in delays_by_responder.values() for delay in delays]
        ),
        "average_hop_count": average(
            [hop for hops in hop_counts_by_responder.values() for hop in hops]
        ),
        "end_to_end_success_rate": percent(actual_reply_count, expected_reply_count),
        "received_replies": received_replies,
        "delays_by_responder": delays_by_responder,
        "hop_counts_by_responder": hop_counts_by_responder,
        "missing_replies": missing_replies,
    }


def print_report(scenario_name, log_path, sink, responders, result):
    request_count = result["request_count"]

    print("===== Simulation Log Analysis =====")
    print("Scenario: %s" % scenario_name)
    print("Log file: %s" % log_path)
    print("Sink node: %d" % sink)
    print("Responder nodes: %s" % ", ".join([str(x) for x in responders]))
    print("Request packets sent by sink: %d" % request_count)
    print("Expected reply packets: %d" % result["expected_reply_count"])
    print(
        "Actual reply packets received by sink: %d" % result["actual_reply_count"]
    )
    print("Packet reception rate: %.2f%%" % result["packet_reception_rate"])
    print("End-to-end success rate: %.2f%%" % result["end_to_end_success_rate"])
    print("Average delay: %.2f ms" % result["average_delay"])
    print("Average hop count: %.2f" % result["average_hop_count"])
    print("")
    print("===== Per-Node Reply Statistics =====")

    for responder in responders:
        received = len(
            [item for item in result["received_replies"] if item[0] == responder]
        )
        expected = request_count
        loss = expected - received
        node_delay = average(result["delays_by_responder"][responder])
        node_hops = average(result["hop_counts_by_responder"][responder])

        print(
            "Responder %d: expected=%d received=%d loss=%d "
            "reception=%.2f%% average_delay=%.2f ms average_hop_count=%.2f"
            % (
                responder,
                expected,
                received,
                loss,
                percent(received, expected),
                node_delay,
                node_hops,
            )
        )

    print("")
    print("===== Missing Reply Pairs =====")
    if result["missing_replies"]:
        for responder, seq in result["missing_replies"]:
            print("node=%d seq=%d" % (responder, seq))
    else:
        print("None")


def build_json_report(scenario_name, log_path, sink, responders, result):
    request_count = result["request_count"]
    per_node = []

    for responder in responders:
        received = len(
            [item for item in result["received_replies"] if item[0] == responder]
        )
        expected = request_count
        loss = expected - received
        per_node.append(
            {
                "node": responder,
                "expected": expected,
                "received": received,
                "loss": loss,
                "reception_rate": percent(received, expected),
                "average_delay": average(result["delays_by_responder"][responder]),
                "average_hop_count": average(
                    result["hop_counts_by_responder"][responder]
                ),
            }
        )

    missing_replies = [
        {"node": responder, "seq": seq}
        for responder, seq in result["missing_replies"]
    ]

    return {
        "schema_version": 1,
        "generated_at": datetime.datetime.utcnow()
        .replace(microsecond=0)
        .isoformat()
        + "Z",
        "scenario": scenario_name,
        "log_path": log_path,
        "sink": sink,
        "responders": responders,
        "overall": {
            "request_count": request_count,
            "expected_reply_count": result["expected_reply_count"],
            "actual_reply_count": result["actual_reply_count"],
            "packet_reception_rate": result["packet_reception_rate"],
            "end_to_end_success_rate": result["end_to_end_success_rate"],
            "average_delay": result["average_delay"],
            "average_hop_count": result["average_hop_count"],
        },
        "per_node": per_node,
        "missing_replies": missing_replies,
    }


def write_json_report(path, report):
    ensure_parent_dir(path)
    with open(path, "w") as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write("\n")


def main():
    args = parse_args()
    scenario_name = args.scenario_option or args.scenario or "baseline"
    config = load_config(scenario_name)
    sink = int(config.get("sink", 1))
    responders = [int(node_id) for node_id in config.get("responders", [])]

    result = analyze_log(args.log, sink, responders)
    print_report(scenario_name, args.log, sink, responders, result)
    if args.json_out:
        write_json_report(
            args.json_out,
            build_json_report(scenario_name, args.log, sink, responders, result),
        )
        print("JSON report saved to %s" % args.json_out)


if __name__ == "__main__":
    main()
