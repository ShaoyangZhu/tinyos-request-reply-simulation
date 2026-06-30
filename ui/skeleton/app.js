const elements = {
  scenarioList: document.getElementById("scenarioList"),
  title: document.getElementById("scenarioTitle"),
  category: document.getElementById("scenarioCategory"),
  command: document.getElementById("commandText"),
  runState: document.getElementById("runState"),
  sink: document.getElementById("sinkValue"),
  responders: document.getElementById("respondersValue"),
  events: document.getElementById("eventsValue"),
  noise: document.getElementById("noiseValue"),
  linkCount: document.getElementById("linkCount"),
  routeMode: document.getElementById("routeMode"),
  routeList: document.getElementById("routeList"),
  topologySvg: document.getElementById("topologySvg"),
  metricStack: document.getElementById("metricStack"),
  statsBody: document.getElementById("statsBody"),
  tableBadge: document.getElementById("tableBadge"),
  flowList: document.getElementById("flowList"),
  logStream: document.getElementById("logStream"),
  reportSnippet: document.getElementById("reportSnippet"),
  runButton: document.getElementById("runButton"),
  inspectButton: document.getElementById("inspectButton"),
  copyCommandButton: document.getElementById("copyCommandButton"),
  copyEvidenceButton: document.getElementById("copyEvidenceButton")
};

let scenarios = {};
let scenarioOrder = [];
let activeScenario = null;
let currentRunState = { text: "Loading scenarios", tone: "yellow" };
let currentJob = null;
let pollTimer = null;
const analysisResults = {};
const apiEnabled = window.location.protocol !== "file:";

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function titleFromName(name) {
  return String(name || "")
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function setState(text, tone = "green") {
  currentRunState = { text, tone };
  elements.runState.textContent = text;
  elements.runState.className = `badge bg-${tone}-lt text-${tone}`;
}

function renderRunState() {
  elements.runState.textContent = currentRunState.text;
  elements.runState.className = `badge bg-${currentRunState.tone}-lt text-${currentRunState.tone}`;
}

window.addEventListener("error", (event) => {
  setState(`UI error: ${event.message}`, "red");
});

function normalizeScenario(raw) {
  const staticRoutes = raw.static_routes || {};
  const routes = Array.isArray(raw.routes)
    ? raw.routes
    : Object.keys(staticRoutes).map((node) => ({
        node: Number(node),
        nextHop: Number(staticRoutes[node])
      }));

  const nodes = Array.isArray(raw.nodes)
    ? raw.nodes.map((item) => {
        if (typeof item === "number") {
          return {
            id: item,
            role: item === raw.sink ? "sink" : "edge"
          };
        }
        return {
          id: Number(item.id),
          role: item.role || (Number(item.id) === raw.sink ? "sink" : "edge")
        };
      })
    : [];

  const edges = Array.isArray(raw.edges)
    ? raw.edges.map((edge) => ({
        src: Number(edge.src),
        dst: Number(edge.dst),
        label: edge.label || `${edge.src}->${edge.dst}`,
        gain: edge.gain,
        variant: edge.variant || ""
      }))
    : [];

  return {
    name: raw.name,
    label: raw.label || titleFromName(raw.name),
    description: raw.description || "",
    category: raw.category || "configured scenario",
    sink: Number(raw.sink || 1),
    responders: (raw.responders || []).map(Number),
    events: raw.event_count || raw.events || 0,
    noise: raw.noise || "configured",
    links: raw.links || edges.length,
    configPath: raw.config_path || raw.configPath || "",
    topoPath: raw.topo_path || raw.topoPath || "",
    routes,
    nodes,
    edges
  };
}

function apiJson(path, options = {}) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const method = options.method || "GET";
    xhr.open(method, path, true);
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.onreadystatechange = () => {
      if (xhr.readyState !== 4) {
        return;
      }

      let payload = {};
      if (xhr.responseText) {
        try {
          payload = JSON.parse(xhr.responseText);
        } catch (error) {
          payload = {};
        }
      }

      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(payload);
      } else {
        reject(new Error(payload.error || `HTTP ${xhr.status}`));
      }
    };
    xhr.onerror = () => reject(new Error("Run API unavailable"));
    xhr.send(options.body || null);
  });
}

function routeForNode(scenario, nodeId) {
  for (let i = 0; i < scenario.routes.length; i += 1) {
    if (Number(scenario.routes[i].node) === Number(nodeId)) {
      return scenario.routes[i];
    }
  }
  return null;
}

function expectedHops(scenario, nodeId) {
  let hops = 1;
  let current = Number(nodeId);
  const seen = {};

  while (current !== scenario.sink && !seen[current]) {
    seen[current] = true;
    const route = routeForNode(scenario, current);
    if (!route) {
      return hops;
    }
    current = Number(route.nextHop);
    if (current !== scenario.sink) {
      hops += 1;
    }
  }

  return hops;
}

function scenarioHealth(scenario) {
  if (scenario.routes.length) {
    return "multi-hop";
  }
  return "configured";
}

function nativeRunCommand(scenarioKey) {
  const logPath = `logs/${scenarioKey}.txt`;
  const resultPath = `ui/results/${scenarioKey}.json`;
  return [
    "make clean",
    "make micaz sim",
    `python sim.py ${scenarioKey} --log ${logPath}`,
    `python analyze_log.py ${scenarioKey} --log ${logPath} --json-out ${resultPath}`
  ].join(" && ");
}

function resultFor(scenarioKey) {
  const result = analysisResults[scenarioKey];
  if (result && result.scenario === scenarioKey) {
    return result;
  }
  return null;
}

function formatPercent(value) {
  if (typeof value !== "number") {
    return "pending";
  }
  return `${value.toFixed(2)}%`;
}

function formatMetric(value, suffix = "") {
  if (typeof value !== "number") {
    return "pending";
  }
  return `${value.toFixed(2)}${suffix}`;
}

function expectedAverageHops(scenario) {
  if (!scenario.responders.length) {
    return 0;
  }

  let total = 0;
  for (let i = 0; i < scenario.responders.length; i += 1) {
    total += expectedHops(scenario, scenario.responders[i]);
  }
  return total / scenario.responders.length;
}

function layoutNodes(scenario) {
  const levels = {};
  const nodesById = {};

  scenario.nodes.forEach((node) => {
    nodesById[node.id] = node;
    levels[node.id] = node.id === scenario.sink ? 0 : expectedHops(scenario, node.id);
  });

  const grouped = {};
  Object.keys(levels).forEach((nodeId) => {
    const level = levels[nodeId];
    if (!grouped[level]) {
      grouped[level] = [];
    }
    grouped[level].push(Number(nodeId));
  });

  const positioned = {};
  Object.keys(grouped).forEach((levelKey) => {
    const level = Number(levelKey);
    const ids = grouped[level].sort((a, b) => a - b);
    const y = 72 + level * 118;
    const span = 520;
    const start = 360 - span / 2;

    ids.forEach((nodeId, index) => {
      const x = ids.length === 1 ? 360 : start + (span * index) / (ids.length - 1);
      const node = nodesById[nodeId];
      positioned[nodeId] = {
        id: nodeId,
        role: node ? node.role : "edge",
        x,
        y
      };
    });
  });

  return positioned;
}

function renderScenarioList() {
  elements.scenarioList.innerHTML = "";

  scenarioOrder.forEach((key) => {
    const scenario = scenarios[key];
    const button = document.createElement("button");
    button.type = "button";
    button.className = `scenario-item${key === activeScenario ? " active" : ""}`;
    button.innerHTML = `
      <strong>${escapeHtml(scenario.label)}</strong>
      <span>${escapeHtml(scenario.category)} · ${scenario.responders.length} responders</span>
    `;
    button.addEventListener("click", () => {
      activeScenario = key;
      render();
    });
    elements.scenarioList.appendChild(button);
  });
}

function renderRoutes(scenario) {
  elements.routeList.innerHTML = "";
  const hasRoutes = scenario.routes.length > 0;
  elements.routeMode.textContent = hasRoutes ? "static next-hop" : "direct reply";
  elements.routeMode.className = hasRoutes ? "badge bg-orange-lt text-orange" : "badge bg-green-lt text-green";

  if (!hasRoutes) {
    const item = document.createElement("div");
    item.className = "list-group-item";
    item.innerHTML = `
      <div class="route-item">
        <div>
          <div class="fw-bold">all responders</div>
          <div class="text-secondary">reply directly to sink ${scenario.sink}</div>
        </div>
        <span class="badge bg-green-lt text-green">single-hop</span>
      </div>
    `;
    elements.routeList.appendChild(item);
    return;
  }

  scenario.routes.forEach((route) => {
    const item = document.createElement("div");
    const hopTone = Number(route.nextHop) === scenario.sink ? "green" : "orange";
    item.className = "list-group-item";
    item.innerHTML = `
      <div class="route-item">
        <div>
          <div class="fw-bold">node ${route.node}</div>
          <div class="text-secondary">next hop ${route.nextHop}</div>
        </div>
        <span class="badge bg-${hopTone}-lt text-${hopTone}">${route.node}->${route.nextHop}</span>
      </div>
    `;
    elements.routeList.appendChild(item);
  });
}

function renderTopologyEmpty(message, detail) {
  const svg = elements.topologySvg;
  svg.innerHTML = "";
  const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
  group.setAttribute("class", "topology-empty");

  const box = document.createElementNS("http://www.w3.org/2000/svg", "rect");
  box.setAttribute("x", 170);
  box.setAttribute("y", 128);
  box.setAttribute("width", 380);
  box.setAttribute("height", 118);
  box.setAttribute("rx", 8);

  const title = document.createElementNS("http://www.w3.org/2000/svg", "text");
  title.setAttribute("x", 360);
  title.setAttribute("y", 174);
  title.setAttribute("class", "empty-title");
  title.textContent = message;

  const body = document.createElementNS("http://www.w3.org/2000/svg", "text");
  body.setAttribute("x", 360);
  body.setAttribute("y", 205);
  body.setAttribute("class", "empty-detail");
  body.textContent = detail;

  group.appendChild(box);
  group.appendChild(title);
  group.appendChild(body);
  svg.appendChild(group);
}

function renderTopology(scenario, result) {
  if (!result) {
    renderTopologyEmpty(
      "No simulation result loaded",
      "Click Run simulation to draw topology for this scenario."
    );
    return;
  }

  const svg = elements.topologySvg;
  const positions = layoutNodes(scenario);
  svg.innerHTML = `
    <defs>
      <marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
        <path d="M0,0 L0,6 L9,3 z" fill="#93a4b7"></path>
      </marker>
    </defs>
  `;

  scenario.edges.forEach((edge) => {
    const a = positions[edge.src];
    const b = positions[edge.dst];
    if (!a || !b) {
      return;
    }

    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("x1", a.x);
    line.setAttribute("y1", a.y);
    line.setAttribute("x2", b.x);
    line.setAttribute("y2", b.y);
    line.setAttribute("class", `topology-link ${edge.variant || ""}`.trim());
    svg.appendChild(line);

    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("x", (a.x + b.x) / 2);
    text.setAttribute("y", (a.y + b.y) / 2 - 8);
    text.setAttribute("class", "link-label");
    text.textContent = edge.label;
    svg.appendChild(text);
  });

  scenario.nodes.forEach((node) => {
    const positioned = positions[node.id];
    if (!positioned) {
      return;
    }

    const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
    group.setAttribute("class", `topology-node ${positioned.role}`);

    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("cx", positioned.x);
    circle.setAttribute("cy", positioned.y);
    circle.setAttribute("r", 28);

    const id = document.createElementNS("http://www.w3.org/2000/svg", "text");
    id.setAttribute("x", positioned.x);
    id.setAttribute("y", positioned.y + 1);
    id.textContent = positioned.id;

    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", positioned.x);
    label.setAttribute("y", positioned.y + 48);
    label.setAttribute("class", "node-label");
    label.textContent = positioned.role;

    group.appendChild(circle);
    group.appendChild(id);
    group.appendChild(label);
    svg.appendChild(group);
  });
}

function metricConfig(scenario, result) {
  if (result && result.overall) {
    const overall = result.overall;
    return [
      ["Packet reception", formatPercent(overall.packet_reception_rate), overall.packet_reception_rate || 0, "green"],
      ["End-to-end", formatPercent(overall.end_to_end_success_rate), overall.end_to_end_success_rate || 0, "primary"],
      ["Avg delay", formatMetric(overall.average_delay, " ms"), Math.min(overall.average_delay || 0, 100), "orange"],
      ["Avg hops", formatMetric(overall.average_hop_count), Math.min((overall.average_hop_count || 0) * 35, 100), "azure"]
    ];
  }

  const routedResponders = scenario.responders.filter((id) => expectedHops(scenario, id) > 1).length;
  return [
    ["Configured responders", String(scenario.responders.length), Math.min(scenario.responders.length * 20, 100), "primary"],
    ["Multi-hop origins", String(routedResponders), Math.min(routedResponders * 35, 100), routedResponders ? "orange" : "green"],
    ["Avg hop target", expectedAverageHops(scenario).toFixed(2), Math.min(expectedAverageHops(scenario) * 35, 100), "azure"],
    ["Simulation data", "not loaded", 0, "secondary"]
  ];
}

function renderMetrics(scenario, result) {
  elements.metricStack.innerHTML = "";
  metricConfig(scenario, result).forEach(([label, value, meter, tone]) => {
    const metric = document.createElement("div");
    metric.className = "metric-row";
    metric.innerHTML = `
      <div class="metric-row-header">
        <span class="text-secondary">${escapeHtml(label)}</span>
        <strong>${escapeHtml(value)}</strong>
      </div>
      <div class="progress">
        <div class="progress-bar bg-${tone}" style="width: ${meter}%"></div>
      </div>
    `;
    elements.metricStack.appendChild(metric);
  });
}

function roleBadgeClass(role) {
  if (role === "sink") {
    return "bg-blue-lt text-blue";
  }
  if (role === "relay") {
    return "bg-orange-lt text-orange";
  }
  return "bg-green-lt text-green";
}

function roleForNode(scenario, nodeId) {
  for (let i = 0; i < scenario.nodes.length; i += 1) {
    if (scenario.nodes[i].id === nodeId) {
      return scenario.nodes[i].role;
    }
  }
  return "edge";
}

function renderStats(scenario, result) {
  elements.statsBody.innerHTML = "";
  elements.tableBadge.textContent = result
    ? `from ${result.log_path || "analysis JSON"}`
    : "waiting for run";

  if (!result) {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td colspan="8" class="empty-cell">
        No per-node simulation data yet. Click Run simulation to populate this table.
      </td>
    `;
    elements.statsBody.appendChild(row);
    return;
  }

  const statsByNode = {};
  if (result && Array.isArray(result.per_node)) {
    result.per_node.forEach((item) => {
      statsByNode[item.node] = item;
    });
  }

  scenario.responders.forEach((nodeId) => {
    const role = roleForNode(scenario, nodeId);
    const stats = statsByNode[nodeId];
    const row = document.createElement("tr");
    row.innerHTML = `
      <td class="fw-bold">node ${nodeId}</td>
      <td><span class="badge role-badge ${roleBadgeClass(role)}">${role}</span></td>
      <td>${stats ? stats.expected : "pending"}</td>
      <td>${stats ? stats.received : '<span class="text-secondary">pending</span>'}</td>
      <td>${stats ? stats.loss : '<span class="text-secondary">pending</span>'}</td>
      <td>${
        stats
          ? `<span class="badge bg-green-lt text-green">${formatPercent(stats.reception_rate)}</span>`
          : '<span class="badge bg-secondary-lt">after run</span>'
      }</td>
      <td>${stats ? formatMetric(stats.average_delay, " ms") : '<span class="text-secondary">after run</span>'}</td>
      <td>${stats ? formatMetric(stats.average_hop_count) : formatMetric(expectedHops(scenario, nodeId))}</td>
    `;
    elements.statsBody.appendChild(row);
  });
}

function renderFlow(scenario) {
  elements.flowList.innerHTML = "";
  const flow = scenario.routes.length
    ? [
        ["REQUEST", "sink sends request packets into the configured topology"],
        ["FORWARD", "nodes with static_routes relay packets by next hop"],
        ["ANALYZE", "analyze_log.py reads RECV_AT_SINK and hop_count fields"]
      ]
    : [
        ["REQUEST", "sink sends request packets"],
        ["REPLY", "responders reply directly to the sink"],
        ["ANALYZE", "analyze_log.py computes per-responder statistics"]
      ];

  flow.forEach(([title, detail]) => {
    const item = document.createElement("li");
    item.className = "step-item";
    item.innerHTML = `
      <div class="h4 m-0">${escapeHtml(title)}</div>
      <span>${escapeHtml(detail)}</span>
    `;
    elements.flowList.appendChild(item);
  });
}

function renderLogs(result) {
  elements.logStream.innerHTML = "";
  let lines =
    currentJob &&
    currentJob.scenario === activeScenario &&
    Array.isArray(currentJob.output_tail) &&
    currentJob.output_tail.length
      ? currentJob.output_tail.slice(-12).map((line) => [
          line,
          currentJob.status === "failed" ? "drop" : currentJob.status === "complete" ? "success" : "forward"
        ])
      : null;

  if (!lines && result) {
    lines = [[`Analysis JSON loaded from ${result.log_path || "log file"}. Run again to see live command output here.`, "success"]];
  }
  if (!lines) {
    lines = [["No run started in this UI session.", ""]];
  }

  lines.forEach(([text, tone]) => {
    const line = document.createElement("div");
    line.className = `log-line ${tone}`.trim();
    line.textContent = text;
    elements.logStream.appendChild(line);
  });
}

function renderReport(scenario, result) {
  if (result && result.overall) {
    const overall = result.overall;
    const missingCount = Array.isArray(result.missing_replies)
      ? result.missing_replies.length
      : 0;
    elements.reportSnippet.textContent = [
      `### ${scenario.label}`,
      "",
      `Generated: ${result.generated_at || "unknown"}`,
      `Log: ${result.log_path || "unknown"}`,
      `Sink: node ${result.sink}`,
      `Responders: ${result.responders.map((id) => `node ${id}`).join(", ")}`,
      "",
      "Analysis result:",
      `- requests: ${overall.request_count}`,
      `- expected replies: ${overall.expected_reply_count}`,
      `- received replies: ${overall.actual_reply_count}`,
      `- packet reception rate: ${formatPercent(overall.packet_reception_rate)}`,
      `- end-to-end success rate: ${formatPercent(overall.end_to_end_success_rate)}`,
      `- average delay: ${formatMetric(overall.average_delay, " ms")}`,
      `- average hop_count: ${formatMetric(overall.average_hop_count)}`,
      `- missing replies: ${missingCount}`,
      "",
      "Missing origin/seq pairs:",
      missingCount
        ? result.missing_replies
            .slice(0, 20)
            .map((item) => `- node ${item.node} seq ${item.seq}`)
            .join("\n")
        : "- none"
    ].join("\n");
    return;
  }

  elements.reportSnippet.textContent = [
    "No report evidence yet.",
    "",
    `Selected scenario: ${scenario.label}`,
    `Config: ${scenario.configPath}`,
    "",
    "Click Run simulation. After analyze_log.py writes JSON, this panel will show the report-ready metrics."
  ].join("\n");
}

function renderEmptyApp(message) {
  elements.scenarioList.innerHTML = "";
  elements.title.textContent = "No scenario loaded";
  elements.category.textContent = "runner unavailable";
  elements.command.textContent = "Start with ./ui/run-ui.sh";
  elements.sink.textContent = "-";
  elements.responders.textContent = "-";
  elements.events.textContent = "-";
  elements.noise.textContent = "-";
  elements.linkCount.textContent = "0 directed links";
  elements.routeList.innerHTML = "";
  elements.metricStack.innerHTML = "";
  elements.statsBody.innerHTML = `<tr><td colspan="8" class="empty-cell">${escapeHtml(message)}</td></tr>`;
  elements.flowList.innerHTML = "";
  elements.logStream.innerHTML = `<div class="log-line drop">${escapeHtml(message)}</div>`;
  elements.reportSnippet.textContent = message;
  renderTopologyEmpty("No scenario loaded", message);
}

function render() {
  if (!activeScenario || !scenarios[activeScenario]) {
    renderEmptyApp(apiEnabled ? "No scenario data returned by /api/scenarios." : "Open this page through ui/run-ui.sh.");
    renderRunState();
    return;
  }

  const scenario = scenarios[activeScenario];
  const result = resultFor(activeScenario);

  renderScenarioList();
  elements.title.textContent = scenario.label;
  elements.category.textContent = `${scenario.category} · ${scenarioHealth(scenario)}`;
  elements.command.textContent = nativeRunCommand(activeScenario);
  renderRunState();
  elements.sink.textContent = scenario.sink;
  elements.responders.textContent = scenario.responders.join(", ");
  elements.events.textContent = Number(scenario.events || 0).toLocaleString();
  elements.noise.textContent = scenario.noise;
  elements.linkCount.textContent = `${scenario.links} directed links`;

  renderRoutes(scenario);
  renderTopology(scenario, result);
  renderMetrics(scenario, result);
  renderStats(scenario, result);
  renderFlow(scenario);
  renderLogs(result);
  renderReport(scenario, result);
}

function copyText(text, successLabel) {
  if (!navigator.clipboard) {
    setState("Clipboard unavailable", "yellow");
    return;
  }

  navigator.clipboard
    .writeText(text)
    .then(() => setState(successLabel, "azure"))
    .catch(() => setState("Clipboard unavailable", "yellow"));
}

function loadScenarios() {
  if (!apiEnabled) {
    setState("Start with ./ui/run-ui.sh", "yellow");
    render();
    return;
  }

  apiJson("/api/scenarios")
    .then((payload) => {
      scenarios = {};
      scenarioOrder = [];
      const list = payload.scenarios || [];
      list.forEach((raw) => {
        const scenario = normalizeScenario(raw);
        scenarios[scenario.name] = scenario;
        scenarioOrder.push(scenario.name);
      });

      activeScenario = scenarioOrder.length ? scenarioOrder[0] : null;
      setState(activeScenario ? "Ready" : "No scenarios found", activeScenario ? "green" : "red");
      render();
    })
    .catch((error) => {
      setState(error.message, "red");
      render();
    });
}

function loadResult(scenarioKey, silent = false) {
  if (!apiEnabled || !scenarioKey) {
    return Promise.resolve();
  }

  return apiJson(`/api/results?scenario=${encodeURIComponent(scenarioKey)}`)
    .then((result) => {
      analysisResults[scenarioKey] = result;
      if (activeScenario === scenarioKey) {
        render();
      }
    })
    .catch(() => {
      if (!silent) {
        setState(`No result yet for ${scenarioKey}`, "yellow");
      }
    });
}

function stopPolling() {
  if (pollTimer) {
    window.clearInterval(pollTimer);
    pollTimer = null;
  }
}

function pollStatus() {
  if (!apiEnabled) {
    return;
  }

  apiJson("/api/status")
    .then((job) => {
      currentJob = job;

      if (currentJob.status === "running") {
        setState(currentJob.message || "Simulation running", "yellow");
        render();
        return;
      }

      if (currentJob.status === "complete") {
        stopPolling();
        setState("Simulation complete. Results loaded.", "green");
        loadResult(currentJob.scenario || activeScenario, false).then(render);
        return;
      }

      if (currentJob.status === "failed") {
        stopPolling();
        setState(currentJob.message || "Simulation failed", "red");
        render();
      }
    })
    .catch(() => {
      stopPolling();
      setState("Run API unavailable", "yellow");
    });
}

function startPolling() {
  stopPolling();
  pollStatus();
  pollTimer = window.setInterval(pollStatus, 1500);
}

function runActiveScenario() {
  if (!apiEnabled) {
    setState("Start with ./ui/run-ui.sh, then open http://localhost:8080/skeleton/", "yellow");
    return;
  }
  if (!activeScenario) {
    setState("No scenario selected", "red");
    return;
  }

  delete analysisResults[activeScenario];
  currentJob = null;
  render();

  apiJson("/api/run", {
    method: "POST",
    body: JSON.stringify({
      scenario: activeScenario,
      build: true
    })
  })
    .then(() => {
      setState(`Running ${activeScenario}`, "yellow");
      startPolling();
    })
    .catch((error) => {
      setState(error.message, "red");
    });
}

elements.runButton.addEventListener("click", runActiveScenario);

elements.inspectButton.addEventListener("click", () => {
  if (activeScenario) {
    loadResult(activeScenario, false);
    setState(`${scenarios[activeScenario].configPath} selected`, "azure");
  }
});

elements.copyCommandButton.addEventListener("click", () => {
  copyText(elements.command.textContent, "Command copied");
});

elements.copyEvidenceButton.addEventListener("click", () => {
  copyText(elements.reportSnippet.textContent, "Evidence copied");
});

render();
loadScenarios();
