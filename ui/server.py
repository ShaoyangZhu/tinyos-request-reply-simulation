#!/usr/bin/env python3
"""Local web runner for the TOSSIM experiment UI.

This server is intended for a Linux VM that already has TinyOS/TOSSIM installed.
It serves the static UI and exposes a small API that starts the native
simulation workflow.
"""

import argparse
import json
import os
import posixpath
import re
import shutil
import subprocess
import threading
import time
import uuid
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import parse_qs, unquote, urlparse


HTTP_OK = 200
HTTP_ACCEPTED = 202
HTTP_BAD_REQUEST = 400
HTTP_NOT_FOUND = 404
HTTP_CONFLICT = 409

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(BASE_DIR)
UI_ROOT = BASE_DIR
SCENARIO_ROOT = os.path.join(REPO_ROOT, "scenarios")
RESULT_ROOT = os.path.join(BASE_DIR, "results")
SCENARIO_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")

JOB_LOCK = threading.Lock()
JOB_STATE = {
    "id": None,
    "scenario": None,
    "status": "idle",
    "started_at": None,
    "finished_at": None,
    "returncode": None,
    "message": "No run started.",
    "log_path": None,
    "result_path": None,
    "runner_log_path": None,
    "output_tail": [],
}


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def relpath(path):
    return os.path.relpath(path, REPO_ROOT).replace(os.sep, "/")


def ensure_dir(path):
    if not os.path.isdir(path):
        os.makedirs(path)


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def title_from_name(name):
    return " ".join([part.capitalize() for part in name.split("_")])


def noise_summary(config):
    noise = config.get("noise", {})
    if not isinstance(noise, dict):
        return "configured"

    model = noise.get("model", "configured")
    value = noise.get("value")
    count = noise.get("count")
    if value is None:
        return str(model)
    if count is None:
        return "%s dBm" % value
    return "%s dBm x %s" % (value, count)


def parse_topology(topo_path):
    edges = []
    if not os.path.isfile(topo_path):
        return edges

    with open(topo_path, "r") as f:
        for line_no, raw_line in enumerate(f, 1):
            line = raw_line.split("#", 1)[0].strip()
            if not line:
                continue

            fields = line.split()
            if len(fields) != 3:
                raise ValueError("%s:%d must have: src dst gain" % (topo_path, line_no))

            src = int(fields[0])
            dst = int(fields[1])
            gain = float(fields[2])
            edges.append({"src": src, "dst": dst, "gain": gain})

    return edges


def display_edges(edges, static_routes):
    route_pairs = set()
    for node_id, next_hop in static_routes.items():
        node = int(node_id)
        hop = int(next_hop)
        route_pairs.add(tuple(sorted([node, hop])))

    pairs = {}
    for edge in edges:
        key = tuple(sorted([edge["src"], edge["dst"]]))
        if key not in pairs:
            pairs[key] = {
                "src": edge["src"],
                "dst": edge["dst"],
                "gain": edge["gain"],
                "directions": set(),
            }
        pairs[key]["directions"].add((edge["src"], edge["dst"]))
        pairs[key]["gain"] = min(pairs[key]["gain"], edge["gain"])

    result = []
    for key in sorted(pairs):
        item = pairs[key]
        bidirectional = len(item["directions"]) > 1
        label = "%d<->%d" % (key[0], key[1]) if bidirectional else "%d->%d" % (
            item["src"],
            item["dst"],
        )
        variant = "route" if key in route_pairs else ""
        if item["gain"] <= -80:
            variant = "weak"
            label = "%s %.0f" % (label, item["gain"])

        result.append(
            {
                "src": key[0],
                "dst": key[1],
                "label": label,
                "gain": item["gain"],
                "variant": variant,
            }
        )

    return result


def node_role(node_id, sink, static_routes):
    if node_id == sink:
        return "sink"
    children = [node for node, hop in static_routes.items() if int(hop) == node_id]
    if children:
        return "relay"
    return "edge"


def scenario_category(config, edges):
    static_routes = config.get("static_routes", {})
    if static_routes:
        return "multi-hop routing"

    gains = [edge["gain"] for edge in edges]
    if gains and min(gains) <= -80:
        return "link quality"

    nodes = config.get("nodes", [])
    if len(nodes) > 3:
        return "scale test"

    return "scale control"


def list_scenarios():
    scenarios = []
    if not os.path.isdir(SCENARIO_ROOT):
        return scenarios

    for name in sorted(os.listdir(SCENARIO_ROOT)):
        scenario_dir = os.path.join(SCENARIO_ROOT, name)
        config_path = os.path.join(scenario_dir, "config.json")
        topo_path = os.path.join(scenario_dir, "topo.txt")
        if not os.path.isdir(scenario_dir) or not os.path.isfile(config_path):
            continue

        config = load_json(config_path)
        static_routes = config.get("static_routes", {})
        topo_edges = parse_topology(topo_path)
        sink = int(config.get("sink", 1))
        nodes = []
        for node_id in config.get("nodes", []):
            node = int(node_id)
            nodes.append({"id": node, "role": node_role(node, sink, static_routes)})

        scenarios.append(
            {
                "name": name,
                "label": title_from_name(config.get("name", name)),
                "description": config.get("description", ""),
                "category": scenario_category(config, topo_edges),
                "config_path": relpath(config_path),
                "topo_path": relpath(topo_path),
                "nodes": nodes,
                "sink": sink,
                "responders": [int(node_id) for node_id in config.get("responders", [])],
                "event_count": config.get("event_count"),
                "noise": noise_summary(config),
                "routes": [
                    {"node": int(node_id), "nextHop": int(next_hop)}
                    for node_id, next_hop in sorted(static_routes.items())
                ],
                "edges": display_edges(topo_edges, static_routes),
            }
        )

    return scenarios


def validate_scenario(name):
    if not name or not SCENARIO_NAME_RE.match(name):
        raise ValueError("Invalid scenario name.")

    scenario_dir = os.path.join(SCENARIO_ROOT, name)
    if not os.path.isdir(scenario_dir):
        raise ValueError("Scenario not found: %s" % name)

    config_path = os.path.join(scenario_dir, "config.json")
    if not os.path.isfile(config_path):
        raise ValueError("Scenario config not found: %s" % relpath(config_path))

    return name


def update_job(**fields):
    with JOB_LOCK:
        JOB_STATE.update(fields)


def append_output(line):
    with JOB_LOCK:
        tail = JOB_STATE.get("output_tail", [])
        tail.append(line.rstrip("\n"))
        JOB_STATE["output_tail"] = tail[-200:]


def snapshot_job():
    with JOB_LOCK:
        return dict(JOB_STATE)


def run_command(command, runner_log):
    append_output("$ " + " ".join(command))
    with open(runner_log, "a") as log:
        log.write("$ " + " ".join(command) + "\n")
        log.flush()

        process = subprocess.Popen(
            command,
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
        )

        for line in process.stdout:
            log.write(line)
            log.flush()
            append_output(line)

        return process.wait()


def run_scenario_job(job_id, scenario, build_first):
    ensure_dir(os.path.join(REPO_ROOT, "logs"))
    ensure_dir(RESULT_ROOT)

    log_path = os.path.join(REPO_ROOT, "logs", "%s.txt" % scenario)
    result_path = os.path.join(RESULT_ROOT, "%s.json" % scenario)
    latest_path = os.path.join(RESULT_ROOT, "latest.json")
    runner_log = os.path.join(RESULT_ROOT, "%s.runner.log" % scenario)
    tossim_python = os.environ.get("TOSSIM_PYTHON", "python")

    update_job(
        id=job_id,
        scenario=scenario,
        status="running",
        started_at=now(),
        finished_at=None,
        returncode=None,
        message="Starting native TOSSIM workflow.",
        log_path=relpath(log_path),
        result_path=relpath(result_path),
        runner_log_path=relpath(runner_log),
        output_tail=[],
    )

    commands = []
    if build_first:
        commands.append(["make", "clean"])
        commands.append(["make", "micaz", "sim"])

    commands.append([tossim_python, "sim.py", scenario, "--log", relpath(log_path)])
    commands.append(
        [
            tossim_python,
            "analyze_log.py",
            scenario,
            "--log",
            relpath(log_path),
            "--json-out",
            relpath(result_path),
        ]
    )

    try:
        with open(runner_log, "w") as log:
            log.write("Scenario: %s\nStarted: %s\n\n" % (scenario, now()))

        for command in commands:
            update_job(message="Running: %s" % " ".join(command))
            returncode = run_command(command, runner_log)
            if returncode != 0:
                update_job(
                    status="failed",
                    finished_at=now(),
                    returncode=returncode,
                    message="Command failed: %s" % " ".join(command),
                )
                return

        if os.path.isfile(result_path):
            shutil.copyfile(result_path, latest_path)

        update_job(
            status="complete",
            finished_at=now(),
            returncode=0,
            message="Simulation and analysis complete.",
        )
    except OSError as error:
        update_job(
            status="failed",
            finished_at=now(),
            returncode=1,
            message="Failed to start command: %s" % error,
        )
    except Exception as error:
        update_job(
            status="failed",
            finished_at=now(),
            returncode=1,
            message="Runner error: %s" % error,
        )


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class TOSSIMUIHandler(SimpleHTTPRequestHandler):
    server_version = "TOSSIMUI/1.0"

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        SimpleHTTPRequestHandler.end_headers(self)

    def translate_path(self, path):
        parsed = urlparse(path)
        request_path = parsed.path
        if request_path in ("", "/"):
            request_path = "/skeleton/index.html"

        request_path = posixpath.normpath(unquote(request_path))
        words = [part for part in request_path.split("/") if part]
        target = UI_ROOT
        for word in words:
            if word in (os.curdir, os.pardir):
                continue
            target = os.path.join(target, word)
        return target

    def write_json(self, status, payload):
        body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_json_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/scenarios":
            self.write_json(HTTP_OK, {"scenarios": list_scenarios()})
            return

        if parsed.path == "/api/status":
            self.write_json(HTTP_OK, snapshot_job())
            return

        if parsed.path == "/api/results":
            query = parse_qs(parsed.query)
            scenario = query.get("scenario", ["latest"])[0]
            if scenario == "latest":
                result_path = os.path.join(RESULT_ROOT, "latest.json")
            else:
                try:
                    validate_scenario(scenario)
                except ValueError as error:
                    self.write_json(HTTP_BAD_REQUEST, {"error": str(error)})
                    return
                result_path = os.path.join(RESULT_ROOT, "%s.json" % scenario)

            if not os.path.isfile(result_path):
                self.write_json(
                    HTTP_NOT_FOUND,
                    {"error": "Result not found.", "path": relpath(result_path)},
                )
                return

            self.write_json(HTTP_OK, load_json(result_path))
            return

        return SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/run":
            self.write_json(HTTP_NOT_FOUND, {"error": "Unknown API endpoint."})
            return

        try:
            payload = self.read_json_body()
            scenario = validate_scenario(payload.get("scenario"))
            build_first = bool(payload.get("build", True))
        except ValueError as error:
            self.write_json(HTTP_BAD_REQUEST, {"error": str(error)})
            return

        current = snapshot_job()
        if current.get("status") == "running":
            self.write_json(
                HTTP_CONFLICT,
                {
                    "error": "A simulation is already running.",
                    "job": current,
                },
            )
            return

        job_id = str(uuid.uuid4())
        thread = threading.Thread(
            target=run_scenario_job,
            args=(job_id, scenario, build_first),
        )
        thread.daemon = True
        thread.start()

        self.write_json(
            HTTP_ACCEPTED,
            {
                "id": job_id,
                "scenario": scenario,
                "status": "running",
                "message": "Simulation started.",
            },
        )


def parse_args():
    parser = argparse.ArgumentParser(description="Serve the TOSSIM UI runner.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    return parser.parse_args()


def main():
    args = parse_args()
    ensure_dir(RESULT_ROOT)
    server = ThreadedHTTPServer((args.host, args.port), TOSSIMUIHandler)
    print("TOSSIM UI runner listening on http://%s:%d/skeleton/" % (args.host, args.port))
    print("Use TOSSIM_PYTHON=python2 if your TinyOS VM requires Python 2 for TOSSIM.")
    server.serve_forever()


if __name__ == "__main__":
    main()
