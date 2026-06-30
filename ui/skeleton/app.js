const scenarios = {
  baseline: {
    label: "Baseline",
    type: "scale",
    sink: 1,
    responders: [2, 3],
    events: 30000,
    noise: "-95 dBm x 100",
    routes: [],
    links: 6,
    nodes: [
      { id: 1, role: "sink", x: 48, y: 44 },
      { id: 2, role: "edge", x: 25, y: 72 },
      { id: 3, role: "edge", x: 72, y: 72 }
    ],
    linkLabels: [
      { text: "1<->2", x: 34, y: 58 },
      { text: "1<->3", x: 59, y: 58 },
      { text: "2<->3", x: 48, y: 78 }
    ]
  },
  four_nodes: {
    label: "Four Nodes",
    type: "scale",
    sink: 1,
    responders: [2, 3, 4],
    events: 40000,
    noise: "-95 dBm x 100",
    routes: [],
    links: 12,
    nodes: [
      { id: 1, role: "sink", x: 48, y: 35 },
      { id: 2, role: "edge", x: 23, y: 65 },
      { id: 3, role: "edge", x: 72, y: 65 },
      { id: 4, role: "edge", x: 48, y: 82 }
    ],
    linkLabels: [
      { text: "full mesh", x: 44, y: 58 }
    ]
  },
  five_nodes: {
    label: "Five Nodes",
    type: "scale",
    sink: 1,
    responders: [2, 3, 4, 5],
    events: 50000,
    noise: "-95 dBm x 100",
    routes: [],
    links: 20,
    nodes: [
      { id: 1, role: "sink", x: 48, y: 32 },
      { id: 2, role: "edge", x: 20, y: 58 },
      { id: 3, role: "edge", x: 76, y: 58 },
      { id: 4, role: "edge", x: 32, y: 82 },
      { id: 5, role: "edge", x: 64, y: 82 }
    ],
    linkLabels: [
      { text: "full mesh", x: 44, y: 60 }
    ]
  },
  weak_link: {
    label: "Weak Link",
    type: "link quality",
    sink: 1,
    responders: [2, 3],
    events: 30000,
    noise: "-95 dBm x 100",
    routes: [],
    links: 6,
    nodes: [
      { id: 1, role: "sink", x: 48, y: 42 },
      { id: 2, role: "edge", x: 25, y: 72 },
      { id: 3, role: "edge", x: 72, y: 72 }
    ],
    linkLabels: [
      { text: "1<->3 -85", x: 58, y: 58 },
      { text: "others -50", x: 30, y: 78 }
    ]
  },
  missing_reverse_link: {
    label: "Missing Reverse",
    type: "asymmetric",
    sink: 1,
    responders: [2, 3],
    events: 30000,
    noise: "-95 dBm x 100",
    routes: [],
    links: 5,
    nodes: [
      { id: 1, role: "sink", x: 48, y: 42 },
      { id: 2, role: "edge", x: 25, y: 72 },
      { id: 3, role: "edge", x: 72, y: 72 }
    ],
    linkLabels: [
      { text: "1->2 only", x: 34, y: 58 },
      { text: "3<->1", x: 60, y: 58 }
    ]
  },
  multihop_chain: {
    label: "Multi-hop Chain",
    type: "multi-hop",
    sink: 1,
    responders: [2, 3, 4, 5],
    events: 50000,
    noise: "-95 dBm x 100",
    routes: [
      { node: 2, nextHop: 1 },
      { node: 3, nextHop: 1 },
      { node: 4, nextHop: 2 },
      { node: 5, nextHop: 3 }
    ],
    links: 8,
    nodes: [
      { id: 1, role: "sink", x: 48, y: 28 },
      { id: 2, role: "relay", x: 30, y: 55 },
      { id: 3, role: "relay", x: 66, y: 55 },
      { id: 4, role: "edge", x: 22, y: 82 },
      { id: 5, role: "edge", x: 74, y: 82 }
    ],
    linkLabels: [
      { text: "4->2->1", x: 25, y: 66 },
      { text: "5->3->1", x: 59, y: 66 }
    ]
  }
};

const sampleMetrics = {
  requestCount: 0,
  expectedReplies: 0,
  receivedReplies: 0,
  prr: "0.00%",
  success: "0.00%",
  delay: "0.00 ms",
  hops: "0.00"
};

const scenarioList = document.getElementById("scenarioList");
const scenarioTitle = document.getElementById("scenarioTitle");
const scenarioType = document.getElementById("scenarioType");
const commandText = document.getElementById("commandText");
const runState = document.getElementById("runState");
const sinkValue = document.getElementById("sinkValue");
const respondersValue = document.getElementById("respondersValue");
const eventsValue = document.getElementById("eventsValue");
const noiseValue = document.getElementById("noiseValue");
const routeList = document.getElementById("routeList");
const topologyCanvas = document.getElementById("topologyCanvas");
const linkCount = document.getElementById("linkCount");
const prrValue = document.getElementById("prrValue");
const successValue = document.getElementById("successValue");
const delayValue = document.getElementById("delayValue");
const hopValue = document.getElementById("hopValue");
const statsBody = document.getElementById("statsBody");
const logStream = document.getElementById("logStream");
const reportSnippet = document.getElementById("reportSnippet");
const runButton = document.getElementById("runButton");
const inspectButton = document.getElementById("inspectButton");
const exportButton = document.getElementById("exportButton");

let activeScenario = "multihop_chain";

function renderScenarioButtons() {
  scenarioList.innerHTML = "";

  Object.entries(scenarios).forEach(([key, scenario]) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `scenario-item${key === activeScenario ? " active" : ""}`;
    button.innerHTML = `<strong>${scenario.label}</strong><span>${scenario.type}</span>`;
    button.addEventListener("click", () => {
      activeScenario = key;
      render();
    });
    scenarioList.appendChild(button);
  });
}

function renderRoutes(scenario) {
  routeList.innerHTML = "";

  if (!scenario.routes.length) {
    const item = document.createElement("li");
    item.innerHTML = "<span>Direct reply model</span><strong>sink 1</strong>";
    routeList.appendChild(item);
    return;
  }

  scenario.routes.forEach((route) => {
    const item = document.createElement("li");
    item.innerHTML = `<span>node ${route.node}</span><strong>${route.node}->${route.nextHop}</strong>`;
    routeList.appendChild(item);
  });
}

function renderTopology(scenario) {
  topologyCanvas.innerHTML = "";

  scenario.nodes.forEach((node) => {
    const element = document.createElement("div");
    element.className = `node ${node.role}`;
    element.style.left = `${node.x}%`;
    element.style.top = `${node.y}%`;
    element.style.transform = "translate(-50%, -50%)";
    element.textContent = node.id;
    topologyCanvas.appendChild(element);
  });

  scenario.linkLabels.forEach((link) => {
    const element = document.createElement("div");
    element.className = "link-label";
    element.style.left = `${link.x}%`;
    element.style.top = `${link.y}%`;
    element.style.transform = "translate(-50%, -50%)";
    element.textContent = link.text;
    topologyCanvas.appendChild(element);
  });
}

function renderStats(scenario) {
  statsBody.innerHTML = "";

  scenario.responders.forEach((node) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${node}</td>
      <td>${sampleMetrics.requestCount}</td>
      <td>${sampleMetrics.receivedReplies}</td>
      <td>0</td>
      <td>${sampleMetrics.prr}</td>
      <td>${sampleMetrics.delay}</td>
      <td>${scenario.routes.some((route) => route.node === node && route.nextHop !== 1) ? "2.00" : "1.00"}</td>
    `;
    statsBody.appendChild(row);
  });
}

function renderLog(scenario) {
  const lines = [
    `SEND_REQ node=1 seq=1 scenario=${activeScenario}`,
    scenario.routes.length ? "FORWARD node=2 type=REQUEST origin=1 to=4 next_hop=4 seq=1" : "SEND_REPLY node=2 to=1 origin=2 seq=1",
    scenario.routes.length ? "FORWARD node=2 type=REPLY origin=4 to=1 next_hop=1 seq=1 hop_count=2" : "RECV_REPLY node=1 from=2 seq=1",
    scenario.routes.length ? "RECV_AT_SINK node=1 origin=4 from=2 seq=1 hop_count=2" : "RECV_AT_SINK node=1 origin=2 from=2 seq=1 hop_count=1"
  ];

  logStream.innerHTML = "";
  lines.forEach((line) => {
    const element = document.createElement("div");
    element.className = "log-line";
    element.textContent = line;
    logStream.appendChild(element);
  });
}

function renderReportSnippet(scenario) {
  const routeText = scenario.routes.length
    ? scenario.routes.map((route) => `${route.node}->${route.nextHop}`).join(", ")
    : "direct replies to sink 1";

  reportSnippet.textContent = [
    `### ${scenario.label}`,
    "",
    `Nodes: ${[scenario.sink, ...scenario.responders].join(", ")}`,
    `Sink: ${scenario.sink}`,
    `Responders: ${scenario.responders.join(", ")}`,
    `Topology links: ${scenario.links}`,
    `Routing: ${routeText}`,
    "",
    "Evidence to fill after a real run:",
    "- Packet reception rate: TODO",
    "- End-to-end success rate: TODO",
    "- Average delay: TODO",
    "- Average hop count: TODO"
  ].join("\n");
}

function render() {
  const scenario = scenarios[activeScenario];
  const command = `sh container/run-in-container.sh ${activeScenario}`;

  renderScenarioButtons();
  scenarioTitle.textContent = activeScenario;
  scenarioType.textContent = scenario.type;
  commandText.textContent = command;
  runState.textContent = "Not started";
  sinkValue.textContent = scenario.sink;
  respondersValue.textContent = scenario.responders.join(", ");
  eventsValue.textContent = scenario.events;
  noiseValue.textContent = scenario.noise;
  linkCount.textContent = `${scenario.links} links`;
  prrValue.textContent = sampleMetrics.prr;
  successValue.textContent = sampleMetrics.success;
  delayValue.textContent = sampleMetrics.delay;
  hopValue.textContent = scenario.routes.length ? "1.50" : "1.00";

  renderRoutes(scenario);
  renderTopology(scenario);
  renderStats(scenario);
  renderLog(scenario);
  renderReportSnippet(scenario);
}

runButton.addEventListener("click", () => {
  runState.textContent = "Command queued";
});

inspectButton.addEventListener("click", () => {
  runState.textContent = "Scenario inspected";
});

exportButton.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(reportSnippet.textContent);
    runState.textContent = "Evidence copied";
  } catch (error) {
    runState.textContent = "Copy unavailable";
  }
});

render();
