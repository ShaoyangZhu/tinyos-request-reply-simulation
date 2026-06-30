from __future__ import print_function
import re

send_req_pattern = re.compile(r"SEND_REQ node=1 seq=(\d+) time=(\d+)")
recv_reply_pattern = re.compile(r"RECV_REPLY node=1 from=(\d+) seq=(\d+) time=(\d+)")

send_times = {}
received_replies = set()
delays = []
delay_points = []
reply_count_by_node = {}

with open("log.txt", "r") as f:
    for line in f:
        m = send_req_pattern.search(line)
        if m:
            seq = int(m.group(1))
            send_time = int(m.group(2))
            send_times[seq] = send_time

        m = recv_reply_pattern.search(line)
        if m:
            src = int(m.group(1))
            seq = int(m.group(2))
            recv_time = int(m.group(3))

            key = (src, seq)

            if key in received_replies:
                continue

            received_replies.add(key)

            if seq in send_times:
                delay = recv_time - send_times[seq]
                delays.append(delay)
                delay_points.append((seq, src, delay))
                reply_count_by_node[src] = reply_count_by_node.get(src, 0) + 1

request_count = len(send_times)

# For each request from node 1, node 2 and node 3 should each send one reply.
expected_reply_count = request_count * 2

actual_reply_count = len(received_replies)

if expected_reply_count > 0:
    packet_reception_rate = float(actual_reply_count) / float(expected_reply_count)
else:
    packet_reception_rate = 0.0

if len(delays) > 0:
    average_delay = sum(delays) / float(len(delays))
else:
    average_delay = 0.0

reply_from_node2 = len([x for x in received_replies if x[0] == 2])
reply_from_node3 = len([x for x in received_replies if x[0] == 3])

if request_count > 0:
    reply_request_ratio = float(actual_reply_count) / float(request_count)
else:
    reply_request_ratio = 0.0


def html_escape(value):
    value = str(value)
    value = value.replace("&", "&amp;")
    value = value.replace("<", "&lt;")
    value = value.replace(">", "&gt;")
    value = value.replace('"', "&quot;")
    return value


def scale(value, min_value, max_value, size):
    if max_value == min_value:
        return size / 2.0
    return (float(value - min_value) / float(max_value - min_value)) * size


def make_delay_svg(points):
    width = 920
    height = 300
    pad_left = 56
    pad_right = 24
    pad_top = 24
    pad_bottom = 46
    plot_width = width - pad_left - pad_right
    plot_height = height - pad_top - pad_bottom

    if len(points) == 0:
        return '<div class="empty-chart">No delay data available.</div>'

    seq_values = [x[0] for x in points]
    delay_values = [x[2] for x in points]
    min_seq = min(seq_values)
    max_seq = max(seq_values)
    min_delay = min(delay_values)
    max_delay = max(delay_values)
    if min_delay == max_delay:
        min_delay = min_delay - 1
        max_delay = max_delay + 1

    sorted_points = sorted(points, key=lambda x: (x[0], x[1]))
    circles = []
    lines_by_node = {}
    color_by_node = {2: "#2f6fed", 3: "#00a884"}

    for seq, src, delay in sorted_points:
        x = pad_left + scale(seq, min_seq, max_seq, plot_width)
        y = pad_top + plot_height - scale(delay, min_delay, max_delay, plot_height)
        color = color_by_node.get(src, "#5a6472")
        lines_by_node.setdefault(src, []).append((x, y))
        circles.append(
            '<circle cx="%.2f" cy="%.2f" r="3.2" fill="%s"><title>seq=%d node=%d delay=%d ms</title></circle>'
            % (x, y, color, seq, src, delay)
        )

    paths = []
    for src in sorted(lines_by_node.keys()):
        pts = lines_by_node[src]
        if len(pts) > 1:
            path = "M " + " L ".join(["%.2f %.2f" % (x, y) for x, y in pts])
            paths.append(
                '<path d="%s" fill="none" stroke="%s" stroke-width="2" opacity="0.75"/>'
                % (path, color_by_node.get(src, "#5a6472"))
            )

    grid = []
    for i in range(5):
        ratio = i / 4.0
        y = pad_top + plot_height * ratio
        value = max_delay - (max_delay - min_delay) * ratio
        grid.append('<line x1="%d" y1="%.2f" x2="%d" y2="%.2f" class="grid-line"/>' % (pad_left, y, width - pad_right, y))
        grid.append('<text x="%d" y="%.2f" class="axis-label" text-anchor="end">%d</text>' % (pad_left - 10, y + 4, value))

    svg = [
        '<svg viewBox="0 0 %d %d" role="img" aria-label="Reply delay chart">' % (width, height),
        '<rect x="0" y="0" width="%d" height="%d" fill="white"/>' % (width, height),
        ''.join(grid),
        '<line x1="%d" y1="%d" x2="%d" y2="%d" class="axis-line"/>' % (pad_left, pad_top, pad_left, height - pad_bottom),
        '<line x1="%d" y1="%d" x2="%d" y2="%d" class="axis-line"/>' % (pad_left, height - pad_bottom, width - pad_right, height - pad_bottom),
        ''.join(paths),
        ''.join(circles),
        '<text x="%d" y="%d" class="axis-label">Sequence number</text>' % (width / 2, height - 12),
        '<text x="18" y="%d" class="axis-label rotate">Delay (ms)</text>' % (height / 2),
        '<text x="%d" y="%d" class="axis-label">seq %d</text>' % (pad_left, height - pad_bottom + 22, min_seq),
        '<text x="%d" y="%d" class="axis-label" text-anchor="end">seq %d</text>' % (width - pad_right, height - pad_bottom + 22, max_seq),
        '</svg>'
    ]
    return "\n".join(svg)


def make_reply_bar_svg(counts):
    width = 540
    height = 220
    pad_left = 70
    pad_right = 30
    pad_bottom = 44
    pad_top = 24
    plot_width = width - pad_left - pad_right
    plot_height = height - pad_top - pad_bottom
    nodes = sorted(counts.keys())
    if len(nodes) == 0:
        return '<div class="empty-chart">No reply data available.</div>'

    max_count = max([counts[node] for node in nodes])
    if max_count == 0:
        max_count = 1

    bar_width = min(86, plot_width / float(len(nodes) * 2))
    pieces = [
        '<svg viewBox="0 0 %d %d" role="img" aria-label="Replies by node">' % (width, height),
        '<rect x="0" y="0" width="%d" height="%d" fill="white"/>' % (width, height),
        '<line x1="%d" y1="%d" x2="%d" y2="%d" class="axis-line"/>' % (pad_left, height - pad_bottom, width - pad_right, height - pad_bottom),
        '<line x1="%d" y1="%d" x2="%d" y2="%d" class="axis-line"/>' % (pad_left, pad_top, pad_left, height - pad_bottom)
    ]

    for index, node in enumerate(nodes):
        count = counts[node]
        x = pad_left + (index + 0.5) * (plot_width / float(len(nodes))) - bar_width / 2.0
        bar_height = (count / float(max_count)) * plot_height
        y = height - pad_bottom - bar_height
        color = "#2f6fed" if node == 2 else "#00a884"
        pieces.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" rx="4" fill="%s"/>' % (x, y, bar_width, bar_height, color))
        pieces.append('<text x="%.2f" y="%.2f" class="bar-value" text-anchor="middle">%d</text>' % (x + bar_width / 2.0, y - 8, count))
        pieces.append('<text x="%.2f" y="%d" class="axis-label" text-anchor="middle">Node %d</text>' % (x + bar_width / 2.0, height - 16, node))

    pieces.append('</svg>')
    return "\n".join(pieces)


def make_table_rows(points, limit):
    rows = []
    for seq, src, delay in sorted(points, key=lambda x: (x[0], x[1]))[:limit]:
        rows.append("<tr><td>%d</td><td>%d</td><td>%d ms</td></tr>" % (seq, src, delay))
    return "\n".join(rows)


def write_html_report(path):
    delay_svg = make_delay_svg(delay_points)
    reply_svg = make_reply_bar_svg(reply_count_by_node)
    table_rows = make_table_rows(delay_points, 40)
    if table_rows == "":
        table_rows = '<tr><td colspan="3">No rows available.</td></tr>'

    html = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>TinyOS Request-Reply Simulation Report</title>
  <style>
    body {
      margin: 0;
      background: #f5f7fb;
      color: #1d2430;
      font-family: Arial, Helvetica, sans-serif;
    }
    header {
      background: #172033;
      color: #fff;
      padding: 28px 36px;
    }
    h1 {
      margin: 0 0 8px;
      font-size: 28px;
      font-weight: 700;
    }
    h2 {
      margin: 0 0 16px;
      font-size: 18px;
    }
    main {
      max-width: 1080px;
      margin: 24px auto 40px;
      padding: 0 20px;
    }
    .summary {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 14px;
      margin-bottom: 18px;
    }
    .metric, .panel {
      background: #fff;
      border: 1px solid #dce3ef;
      border-radius: 8px;
      box-shadow: 0 1px 3px rgba(23, 32, 51, 0.06);
    }
    .metric {
      padding: 16px;
    }
    .metric-label {
      color: #5f6b7a;
      font-size: 13px;
      margin-bottom: 8px;
    }
    .metric-value {
      font-size: 26px;
      font-weight: 700;
      line-height: 1.1;
    }
    .panel {
      margin-top: 18px;
      padding: 18px;
    }
    .chart-row {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(320px, 0.58fr);
      gap: 18px;
    }
    .legend {
      display: flex;
      gap: 18px;
      color: #5f6b7a;
      font-size: 13px;
      margin-bottom: 8px;
    }
    .dot {
      display: inline-block;
      width: 10px;
      height: 10px;
      border-radius: 50%%;
      margin-right: 6px;
    }
    .node2 { background: #2f6fed; }
    .node3 { background: #00a884; }
    .grid-line { stroke: #e6ebf2; stroke-width: 1; }
    .axis-line { stroke: #9aa6b5; stroke-width: 1.2; }
    .axis-label { fill: #5f6b7a; font-size: 12px; }
    .rotate { transform: rotate(-90deg); transform-origin: 18px 150px; }
    .bar-value { fill: #1d2430; font-size: 13px; font-weight: 700; }
    table {
      width: 100%%;
      border-collapse: collapse;
      font-size: 14px;
    }
    th, td {
      border-bottom: 1px solid #e6ebf2;
      padding: 9px 10px;
      text-align: left;
    }
    th {
      color: #5f6b7a;
      font-weight: 700;
      background: #f9fbfe;
    }
    .empty-chart {
      padding: 32px;
      color: #5f6b7a;
      background: #fff;
    }
    @media (max-width: 800px) {
      header { padding: 22px 20px; }
      .chart-row { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <h1>TinyOS Request-Reply Simulation Report</h1>
    <div>Generated from log.txt</div>
  </header>
  <main>
    <section class="summary">
      <div class="metric"><div class="metric-label">Requests sent by node 1</div><div class="metric-value">%(request_count)d</div></div>
      <div class="metric"><div class="metric-label">Expected replies</div><div class="metric-value">%(expected_reply_count)d</div></div>
      <div class="metric"><div class="metric-label">Actual replies</div><div class="metric-value">%(actual_reply_count)d</div></div>
      <div class="metric"><div class="metric-label">Reply success rate</div><div class="metric-value">%(packet_reception_rate).2f%%</div></div>
      <div class="metric"><div class="metric-label">Replies per request</div><div class="metric-value">%(reply_request_ratio).2f</div></div>
      <div class="metric"><div class="metric-label">Average delay</div><div class="metric-value">%(average_delay).2f ms</div></div>
    </section>

    <section class="chart-row">
      <div class="panel">
        <h2>Reply Delay by Sequence</h2>
        <div class="legend">
          <span><span class="dot node2"></span>Node 2</span>
          <span><span class="dot node3"></span>Node 3</span>
        </div>
        %(delay_svg)s
      </div>
      <div class="panel">
        <h2>Replies by Node</h2>
        %(reply_svg)s
      </div>
    </section>

    <section class="panel">
      <h2>First 40 Reply Delay Records</h2>
      <table>
        <thead><tr><th>Sequence</th><th>Reply Node</th><th>Delay</th></tr></thead>
        <tbody>
          %(table_rows)s
        </tbody>
      </table>
    </section>
  </main>
</body>
</html>
""" % {
        "request_count": request_count,
        "expected_reply_count": expected_reply_count,
        "actual_reply_count": actual_reply_count,
        "packet_reception_rate": packet_reception_rate * 100.0,
        "reply_request_ratio": reply_request_ratio,
        "average_delay": average_delay,
        "delay_svg": delay_svg,
        "reply_svg": reply_svg,
        "table_rows": table_rows,
    }

    with open(path, "w") as f:
        f.write(html)

print("===== Simulation Log Analysis =====")
print("Request packets sent by node 1: %d" % request_count)
print("Expected reply packets: %d" % expected_reply_count)
print("Actual reply packets received by node 1: %d" % actual_reply_count)
print("Reply packets from node 2: %d" % reply_from_node2)
print("Reply packets from node 3: %d" % reply_from_node3)
print("Packet reception rate: %.2f%%" % (packet_reception_rate * 100.0))
print("Replies per request: %.2f" % reply_request_ratio)
print("Average delay: %.2f ms" % average_delay)

write_html_report("report.html")
print("HTML report generated: report.html")
