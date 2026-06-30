const scenarios = {
  baseline: {
    label: "Baseline",
    category: "scale control",
    type: "single-hop",
    sink: 1,
    responders: [2, 3],
    events: 30000,
    noise: "-95 dBm x 100",
    links: 6,
    configPath: "scenarios/baseline/config.json",
    topoPath: "scenarios/baseline/topo.txt",
    routes: [],
    nodes: [
      { id: 1, role: "sink", x: 360, y: 105 },
      { id: 2, role: "edge", x: 230, y: 255 },
      { id: 3, role: "edge", x: 490, y: 255 }
    ],
    edges: [
      [1, 2, "1<->2"],
      [1, 3, "1<->3"],
      [2, 3, "2<->3"]
    ],
    flow: [
      ["SEND_REQ", "node 1 broadcasts a request sequence"],
      ["SEND_REPLY", "nodes 2 and 3 reply after staggered timers"],
      ["RECV_AT_SINK", "node 1 records origin, sequence, and delay"]
    ],
    log: [
      ["SEND_REQ node=1 seq=1 origin=1 hop_count=0", ""],
      ["SEND_REPLY node=2 to=1 origin=2 seq=1 hop_count=1", ""],
      ["RECV_AT_SINK node=1 origin=2 from=2 seq=1 hop_count=1", "success"],
      ["SEND_REPLY node=3 to=1 origin=3 seq=1 hop_count=1", ""]
    ]
  },
  four_nodes: {
    label: "Four Nodes",
    category: "scale test",
    type: "single-hop",
    sink: 1,
    responders: [2, 3, 4],
    events: 40000,
    noise: "-95 dBm x 100",
    links: 12,
    configPath: "scenarios/four_nodes/config.json",
    topoPath: "scenarios/four_nodes/topo.txt",
    routes: [],
    nodes: [
      { id: 1, role: "sink", x: 360, y: 78 },
      { id: 2, role: "edge", x: 215, y: 210 },
      { id: 3, role: "edge", x: 505, y: 210 },
      { id: 4, role: "edge", x: 360, y: 300 }
    ],
    edges: [
      [1, 2, "1<->2"],
      [1, 3, "1<->3"],
      [1, 4, "1<->4"],
      [2, 4, "2<->4"],
      [3, 4, "3<->4"]
    ],
    flow: [
      ["SEND_REQ", "sink reaches three responders"],
      ["REPLY FAN-IN", "three replies converge at node 1"],
      ["ANALYZE", "per-node rows are generated from responders"]
    ],
    log: [
      ["SEND_REQ node=1 seq=1 origin=1 hop_count=0", ""],
      ["RECV_AT_SINK node=1 origin=2 from=2 seq=1 hop_count=1", "success"],
      ["RECV_AT_SINK node=1 origin=3 from=3 seq=1 hop_count=1", "success"],
      ["RECV_AT_SINK node=1 origin=4 from=4 seq=1 hop_count=1", "success"]
    ]
  },
  five_nodes: {
    label: "Five Nodes",
    category: "scale test",
    type: "single-hop",
    sink: 1,
    responders: [2, 3, 4, 5],
    events: 50000,
    noise: "-95 dBm x 100",
    links: 20,
    configPath: "scenarios/five_nodes/config.json",
    topoPath: "scenarios/five_nodes/topo.txt",
    routes: [],
    nodes: [
      { id: 1, role: "sink", x: 360, y: 70 },
      { id: 2, role: "edge", x: 175, y: 190 },
      { id: 3, role: "edge", x: 545, y: 190 },
      { id: 4, role: "edge", x: 250, y: 310 },
      { id: 5, role: "edge", x: 470, y: 310 }
    ],
    edges: [
      [1, 2, "1<->2"],
      [1, 3, "1<->3"],
      [1, 4, "1<->4"],
      [1, 5, "1<->5"],
      [4, 5, "4<->5"]
    ],
    flow: [
      ["SEND_REQ", "node 1 reaches four responders"],
      ["EXPECTED", "analysis expects four replies per request sequence"],
      ["COMPARE", "node count changes can support deployment discussion"]
    ],
    log: [
      ["SEND_REQ node=1 seq=1 origin=1 hop_count=0", ""],
      ["RECV_AT_SINK node=1 origin=2 from=2 seq=1 hop_count=1", "success"],
      ["RECV_AT_SINK node=1 origin=3 from=3 seq=1 hop_count=1", "success"],
      ["RECV_AT_SINK node=1 origin=4 from=4 seq=1 hop_count=1", "success"],
      ["RECV_AT_SINK node=1 origin=5 from=5 seq=1 hop_count=1", "success"]
    ]
  },
  weak_link: {
    label: "Weak Link",
    category: "link quality",
    type: "loss model",
    sink: 1,
    responders: [2, 3],
    events: 30000,
    noise: "-95 dBm x 100",
    links: 6,
    configPath: "scenarios/weak_link/config.json",
    topoPath: "scenarios/weak_link/topo.txt",
    routes: [],
    nodes: [
      { id: 1, role: "sink", x: 360, y: 105 },
      { id: 2, role: "edge", x: 230, y: 255 },
      { id: 3, role: "edge", x: 490, y: 255 }
    ],
    edges: [
      [1, 2, "1<->2"],
      [1, 3, "weak -85", "weak"],
      [2, 3, "2<->3"]
    ],
    flow: [
      ["SEND_REQ", "node 1 reaches node 2 and weakly reaches node 3"],
      ["LOSS PRESSURE", "weak gain should reduce node 3 delivery"],
      ["COMPARE PRR", "analysis compares node 3 against node 2"]
    ],
    log: [
      ["SEND_REQ node=1 seq=1 origin=1 hop_count=0", ""],
      ["RECV_AT_SINK node=1 origin=2 from=2 seq=1 hop_count=1", "success"],
      ["MISSING_REPLY origin=3 seq=1 reason=weak_link", "drop"]
    ]
  },
  missing_reverse_link: {
    label: "Missing Reverse",
    category: "asymmetric link",
    type: "failure mode",
    sink: 1,
    responders: [2, 3],
    events: 30000,
    noise: "-95 dBm x 100",
    links: 5,
    configPath: "scenarios/missing_reverse_link/config.json",
    topoPath: "scenarios/missing_reverse_link/topo.txt",
    routes: [],
    nodes: [
      { id: 1, role: "sink", x: 360, y: 105 },
      { id: 2, role: "edge", x: 230, y: 255 },
      { id: 3, role: "edge", x: 490, y: 255 }
    ],
    edges: [
      [1, 2, "1->2"],
      [1, 3, "1<->3"],
      [2, 3, "2<->3"]
    ],
    flow: [
      ["ONE-WAY", "node 1 can reach node 2"],
      ["REVERSE FAIL", "node 2 cannot reply directly to node 1"],
      ["MISSING PAIR", "analysis exposes node and sequence gaps"]
    ],
    log: [
      ["SEND_REQ node=1 seq=1 origin=1 hop_count=0", ""],
      ["SEND_REPLY node=2 to=1 origin=2 seq=1 hop_count=1", ""],
      ["MISSING_REPLY origin=2 seq=1 reason=no_reverse_link", "drop"],
      ["RECV_AT_SINK node=1 origin=3 from=3 seq=1 hop_count=1", "success"]
    ]
  },
  multihop_chain: {
    label: "Multi-hop Chain",
    category: "multi-hop routing",
    type: "network layer",
    sink: 1,
    responders: [2, 3, 4, 5],
    events: 50000,
    noise: "-95 dBm x 100",
    links: 8,
    configPath: "scenarios/multihop_chain/config.json",
    topoPath: "scenarios/multihop_chain/topo.txt",
    routes: [
      { node: 2, nextHop: 1 },
      { node: 3, nextHop: 1 },
      { node: 4, nextHop: 2 },
      { node: 5, nextHop: 3 }
    ],
    nodes: [
      { id: 1, role: "sink", x: 360, y: 70 },
      { id: 2, role: "relay", x: 240, y: 185 },
      { id: 3, role: "relay", x: 480, y: 185 },
      { id: 4, role: "edge", x: 165, y: 310 },
      { id: 5, role: "edge", x: 555, y: 310 }
    ],
    edges: [
      [4, 2, "4->2", "route"],
      [2, 1, "2->1", "route"],
      [5, 3, "5->3", "route"],
      [3, 1, "3->1", "route"]
    ],
    flow: [
      ["REQUEST", "sink sends the request toward relay layer"],
      ["FORWARD", "node 2 reaches node 4, node 3 reaches node 5"],
      ["STATIC ROUTE", "node 4 replies through 2 and node 5 through 3"],
      ["RECV_AT_SINK", "sink records origin and hop_count"]
    ],
    log: [
      ["SEND_REQ node=1 seq=1 origin=1 hop_count=0", ""],
      ["FORWARD node=2 type=REQUEST origin=1 to=4 next_hop=4 seq=1 hop_count=1", "forward"],
      ["SEND_REPLY node=4 to=2 origin=4 seq=1 hop_count=1", ""],
      ["FORWARD node=2 type=REPLY origin=4 to=1 next_hop=1 seq=1 hop_count=2", "forward"],
      ["RECV_AT_SINK node=1 origin=4 from=2 seq=1 hop_count=2", "success"]
    ]
  }
};

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

let activeScenario = "multihop_chain";

function byId(scenario, id) {
  return scenario.nodes.find((node) => node.id === id);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function setState(text, tone = "green") {
  elements.runState.textContent = text;
  elements.runState.className = `badge bg-${tone}-lt text-${tone}`;
}

function expectedHops(scenario, nodeId) {
  const route = scenario.routes.find((item) => item.node === nodeId);
  if (!route) {
    return 1;
  }
  return route.nextHop === scenario.sink ? 1 : 2;
}

function scenarioHealth(scenario) {
  if (scenario.routes.length) {
    return "multi-hop";
  }
  if (scenario.type === "failure mode") {
    return "asymmetric";
  }
  if (scenario.type === "loss model") {
    return "weak link";
  }
  return "direct";
}

function renderScenarioList() {
  elements.scenarioList.innerHTML = "";

  Object.entries(scenarios).forEach(([key, scenario]) => {
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
    const hopTone = route.nextHop === scenario.sink ? "green" : "orange";
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

function renderTopology(scenario) {
  const svg = elements.topologySvg;
  svg.innerHTML = `
    <defs>
      <marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
        <path d="M0,0 L0,6 L9,3 z" fill="#93a4b7"></path>
      </marker>
    </defs>
  `;

  scenario.edges.forEach(([from, to, label, variant]) => {
    const a = byId(scenario, from);
    const b = byId(scenario, to);
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("x1", a.x);
    line.setAttribute("y1", a.y);
    line.setAttribute("x2", b.x);
    line.setAttribute("y2", b.y);
    line.setAttribute("class", `topology-link ${variant || ""}`.trim());
    svg.appendChild(line);

    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("x", (a.x + b.x) / 2);
    text.setAttribute("y", (a.y + b.y) / 2 - 8);
    text.setAttribute("class", "link-label");
    text.textContent = label;
    svg.appendChild(text);
  });

  scenario.nodes.forEach((node) => {
    const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
    group.setAttribute("class", `topology-node ${node.role}`);

    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("cx", node.x);
    circle.setAttribute("cy", node.y);
    circle.setAttribute("r", 28);

    const id = document.createElementNS("http://www.w3.org/2000/svg", "text");
    id.setAttribute("x", node.x);
    id.setAttribute("y", node.y + 1);
    id.textContent = node.id;

    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", node.x);
    label.setAttribute("y", node.y + 48);
    label.setAttribute("class", "node-label");
    label.textContent = node.role;

    group.appendChild(circle);
    group.appendChild(id);
    group.appendChild(label);
    svg.appendChild(group);
  });
}

function metricConfig(scenario) {
  const expectedReplies = scenario.responders.length;
  const routedResponders = scenario.responders.filter((id) => expectedHops(scenario, id) > 1).length;
  return [
    ["Expected replies", `${expectedReplies} / seq`, Math.min(expectedReplies * 20, 100), "primary"],
    ["Multi-hop origins", String(routedResponders), Math.min(routedResponders * 35, 100), routedResponders ? "orange" : "green"],
    ["Avg hop target", expectedAverageHops(scenario).toFixed(2), Math.min(expectedAverageHops(scenario) * 35, 100), "azure"],
    ["Real run status", "pending", 0, "secondary"]
  ];
}

function expectedAverageHops(scenario) {
  if (!scenario.responders.length) {
    return 0;
  }
  const total = scenario.responders.reduce((sum, id) => sum + expectedHops(scenario, id), 0);
  return total / scenario.responders.length;
}

function renderMetrics(scenario) {
  elements.metricStack.innerHTML = "";

  metricConfig(scenario).forEach(([label, value, meter, tone]) => {
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

function roleForNode(scenario, nodeId) {
  const node = byId(scenario, nodeId);
  return node ? node.role : "edge";
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

function renderStats(scenario) {
  elements.statsBody.innerHTML = "";
  elements.tableBadge.textContent = `${scenario.responders.length} responders`;

  scenario.responders.forEach((nodeId) => {
    const role = roleForNode(scenario, nodeId);
    const hops = expectedHops(scenario, nodeId);
    const row = document.createElement("tr");
    row.innerHTML = `
      <td class="fw-bold">node ${nodeId}</td>
      <td><span class="badge role-badge ${roleBadgeClass(role)}">${role}</span></td>
      <td>1 / seq</td>
      <td><span class="text-secondary">pending</span></td>
      <td><span class="text-secondary">pending</span></td>
      <td><span class="badge bg-secondary-lt">after run</span></td>
      <td><span class="text-secondary">after run</span></td>
      <td>${hops.toFixed(2)}</td>
    `;
    elements.statsBody.appendChild(row);
  });
}

function renderFlow(scenario) {
  elements.flowList.innerHTML = "";

  scenario.flow.forEach(([title, detail]) => {
    const item = document.createElement("li");
    item.className = "step-item";
    item.innerHTML = `
      <div class="h4 m-0">${escapeHtml(title)}</div>
      <span>${escapeHtml(detail)}</span>
    `;
    elements.flowList.appendChild(item);
  });
}

function renderLogs(scenario) {
  elements.logStream.innerHTML = "";
  scenario.log.forEach(([text, tone]) => {
    const line = document.createElement("div");
    line.className = `log-line ${tone}`.trim();
    line.textContent = text;
    elements.logStream.appendChild(line);
  });
}

function renderReport(scenario) {
  const routeText = scenario.routes.length
    ? scenario.routes.map((route) => `${route.node}->${route.nextHop}`).join(", ")
    : `responders reply directly to sink ${scenario.sink}`;

  const nonDirect = scenario.responders
    .filter((id) => expectedHops(scenario, id) > 1)
    .map((id) => `node ${id}`);

  elements.reportSnippet.textContent = [
    `### ${scenario.label}`,
    "",
    `Config: ${scenario.configPath}`,
    `Topology: ${scenario.topoPath}`,
    `Experiment type: ${scenario.category}`,
    `Sink: node ${scenario.sink}`,
    `Responders: ${scenario.responders.map((id) => `node ${id}`).join(", ")}`,
    `Directed links: ${scenario.links}`,
    `Routing: ${routeText}`,
    `Expected hop average: ${expectedAverageHops(scenario).toFixed(2)}`,
    "",
    nonDirect.length
      ? `Non-direct sink nodes: ${nonDirect.join(", ")}`
      : "Non-direct sink nodes: none in this scenario",
    "",
    "After a real run, fill these from analyze_log.py:",
    "- packet reception rate",
    "- end-to-end success rate",
    "- average delay by origin",
    "- average hop_count",
    "- missing origin/seq pairs"
  ].join("\n");
}

function render() {
  const scenario = scenarios[activeScenario];

  renderScenarioList();
  elements.title.textContent = `${scenario.label}`;
  elements.category.textContent = `${scenario.category} · ${scenarioHealth(scenario)}`;
  elements.command.textContent = `sh container/run-in-container.sh ${activeScenario}`;
  setState("Ready", "green");
  elements.sink.textContent = scenario.sink;
  elements.responders.textContent = scenario.responders.join(", ");
  elements.events.textContent = scenario.events.toLocaleString();
  elements.noise.textContent = scenario.noise;
  elements.linkCount.textContent = `${scenario.links} directed links`;

  renderRoutes(scenario);
  renderTopology(scenario);
  renderMetrics(scenario);
  renderStats(scenario);
  renderFlow(scenario);
  renderLogs(scenario);
  renderReport(scenario);
}

async function copyText(text, successLabel) {
  try {
    await navigator.clipboard.writeText(text);
    setState(successLabel, "azure");
  } catch (error) {
    setState("Clipboard unavailable", "yellow");
  }
}

elements.runButton.addEventListener("click", () => {
  setState("Preview queued. No simulation was started.", "yellow");
});

elements.inspectButton.addEventListener("click", () => {
  const scenario = scenarios[activeScenario];
  setState(`${scenario.configPath} selected`, "azure");
});

elements.copyCommandButton.addEventListener("click", () => {
  copyText(elements.command.textContent, "Command copied");
});

elements.copyEvidenceButton.addEventListener("click", () => {
  copyText(elements.reportSnippet.textContent, "Evidence copied");
});

render();
