from __future__ import print_function
import os
import re
import sys


SEND_REQ_PATTERN = re.compile(r"SEND_REQ node=1 seq=(\d+) time=(\d+)")
RECV_REPLY_PATTERN = re.compile(r"RECV_REPLY node=1 from=(\d+) seq=(\d+) time=(\d+)")

COLORS = {
    2: "#2f6fed",
    3: "#00a884",
    4: "#f59f00",
    5: "#d6336c",
    6: "#7048e8",
}


def html_escape(value):
    value = str(value)
    value = value.replace("&", "&amp;")
    value = value.replace("<", "&lt;")
    value = value.replace(">", "&gt;")
    value = value.replace('"', "&quot;")
    return value


def parse_int_list(value):
    result = []
    for item in value.split(","):
        item = item.strip()
        if item != "":
            result.append(int(item))
    return result


def report_name_for_log(log_path):
    base = os.path.splitext(os.path.basename(log_path))[0]
    if base == "log":
        return "report.html"
    return "report_%s.html" % base


def scale(value, min_value, max_value, size):
    if max_value == min_value:
        return size / 2.0
    return (float(value - min_value) / float(max_value - min_value)) * size


def analyze_log(log_path):
    metadata = {}
    send_times = {}
    received_replies = set()
    delays = []
    delay_points = []
    reply_count_by_node = {}

    with open(log_path, "r") as f:
        for line in f:
            line = line.strip()

            if line.startswith("#"):
                if ":" in line:
                    key, value = line[1:].split(":", 1)
                    metadata[key.strip()] = value.strip()
                continue

            m = SEND_REQ_PATTERN.search(line)
            if m:
                seq = int(m.group(1))
                send_times[seq] = int(m.group(2))

            m = RECV_REPLY_PATTERN.search(line)
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

    if "RESPONDER_NODES" in metadata:
        responder_nodes = parse_int_list(metadata["RESPONDER_NODES"])
    else:
        responder_nodes = sorted(reply_count_by_node.keys())
        if len(responder_nodes) == 0:
            responder_nodes = [2, 3]

    request_count = len(send_times)
    expected_reply_count = request_count * len(responder_nodes)
    actual_reply_count = len(received_replies)

    if expected_reply_count > 0:
        packet_reception_rate = float(actual_reply_count) / float(expected_reply_count)
    else:
        packet_reception_rate = 0.0

    if request_count > 0:
        reply_request_ratio = float(actual_reply_count) / float(request_count)
    else:
        reply_request_ratio = 0.0

    if len(delays) > 0:
        average_delay = sum(delays) / float(len(delays))
    else:
        average_delay = 0.0

    return {
        "log_path": log_path,
        "metadata": metadata,
        "responder_nodes": responder_nodes,
        "request_count": request_count,
        "expected_reply_count": expected_reply_count,
        "actual_reply_count": actual_reply_count,
        "packet_reception_rate": packet_reception_rate,
        "reply_request_ratio": reply_request_ratio,
        "average_delay": average_delay,
        "reply_count_by_node": reply_count_by_node,
        "delay_points": delay_points,
    }


def make_delay_svg(points):
    width = 920
    height = 320
    pad_left = 56
    pad_right = 24
    pad_top = 24
    pad_bottom = 50
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

    circles = []
    lines_by_node = {}
    for seq, src, delay in sorted(points, key=lambda x: (x[0], x[1])):
        x = pad_left + scale(seq, min_seq, max_seq, plot_width)
        y = pad_top + plot_height - scale(delay, min_delay, max_delay, plot_height)
        color = COLORS.get(src, "#5a6472")
        lines_by_node.setdefault(src, []).append((x, y))
        circles.append(
            '<circle cx="%.2f" cy="%.2f" r="2.8" fill="%s"><title>seq=%d node=%d delay=%d ms</title></circle>'
            % (x, y, color, seq, src, delay)
        )

    grid = []
    for i in range(5):
        ratio = i / 4.0
        y = pad_top + plot_height * ratio
        value = int(max_delay - (max_delay - min_delay) * ratio)
        grid.append('<line x1="%d" y1="%.2f" x2="%d" y2="%.2f" class="grid-line"/>' % (pad_left, y, width - pad_right, y))
        grid.append('<text x="%d" y="%.2f" class="axis-label" text-anchor="end">%d</text>' % (pad_left - 10, y + 4, value))

    paths = []
    for src in sorted(lines_by_node.keys()):
        pts = lines_by_node[src]
        if len(pts) > 1:
            path = "M " + " L ".join(["%.2f %.2f" % (x, y) for x, y in pts])
            paths.append('<path d="%s" fill="none" stroke="%s" stroke-width="1.8" opacity="0.62"/>' % (path, COLORS.get(src, "#5a6472")))

    svg = [
        '<svg viewBox="0 0 %d %d" role="img" aria-label="Reply delay chart">' % (width, height),
        '<rect x="0" y="0" width="%d" height="%d" fill="white"/>' % (width, height),
        ''.join(grid),
        '<line x1="%d" y1="%d" x2="%d" y2="%d" class="axis-line"/>' % (pad_left, pad_top, pad_left, height - pad_bottom),
        '<line x1="%d" y1="%d" x2="%d" y2="%d" class="axis-line"/>' % (pad_left, height - pad_bottom, width - pad_right, height - pad_bottom),
        ''.join(paths),
        ''.join(circles),
        '<text x="%d" y="%d" class="axis-label">Sequence number</text>' % (width / 2, height - 14),
        '<text x="%d" y="%d" class="axis-label">seq %d</text>' % (pad_left, height - pad_bottom + 22, min_seq),
        '<text x="%d" y="%d" class="axis-label" text-anchor="end">seq %d</text>' % (width - pad_right, height - pad_bottom + 22, max_seq),
        '</svg>'
    ]
    return "\n".join(svg)


def make_reply_bar_svg(counts, responder_nodes):
    width = 680
    height = 240
    pad_left = 70
    pad_right = 30
    pad_bottom = 46
    pad_top = 28
    plot_width = width - pad_left - pad_right
    plot_height = height - pad_top - pad_bottom
    nodes = sorted(responder_nodes)

    if len(nodes) == 0:
        return '<div class="empty-chart">No reply data available.</div>'

    max_count = max([counts.get(node, 0) for node in nodes])
    if max_count == 0:
        max_count = 1

    bar_width = min(70, plot_width / float(len(nodes) * 2))
    pieces = [
        '<svg viewBox="0 0 %d %d" role="img" aria-label="Replies by node">' % (width, height),
        '<rect x="0" y="0" width="%d" height="%d" fill="white"/>' % (width, height),
        '<line x1="%d" y1="%d" x2="%d" y2="%d" class="axis-line"/>' % (pad_left, height - pad_bottom, width - pad_right, height - pad_bottom),
        '<line x1="%d" y1="%d" x2="%d" y2="%d" class="axis-line"/>' % (pad_left, pad_top, pad_left, height - pad_bottom)
    ]

    for index, node in enumerate(nodes):
        count = counts.get(node, 0)
        x = pad_left + (index + 0.5) * (plot_width / float(len(nodes))) - bar_width / 2.0
        bar_height = (count / float(max_count)) * plot_height
        y = height - pad_bottom - bar_height
        color = COLORS.get(node, "#5a6472")
        pieces.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" rx="4" fill="%s"/>' % (x, y, bar_width, bar_height, color))
        pieces.append('<text x="%.2f" y="%.2f" class="bar-value" text-anchor="middle">%d</text>' % (x + bar_width / 2.0, y - 8, count))
        pieces.append('<text x="%.2f" y="%d" class="axis-label" text-anchor="middle">Node %d</text>' % (x + bar_width / 2.0, height - 16, node))

    pieces.append('</svg>')
    return "\n".join(pieces)


def make_legend(responder_nodes):
    items = []
    for node in sorted(responder_nodes):
        items.append('<span><span class="dot" style="background:%s"></span>Node %d</span>' % (COLORS.get(node, "#5a6472"), node))
    return "\n".join(items)


def make_table_rows(points, limit):
    rows = []
    for seq, src, delay in sorted(points, key=lambda x: (x[0], x[1]))[:limit]:
        rows.append("<tr><td>%d</td><td>%d</td><td>%d ms</td></tr>" % (seq, src, delay))
    if len(rows) == 0:
        return '<tr><td colspan="3">No rows available.</td></tr>'
    return "\n".join(rows)


def make_metadata_rows(metadata):
    keys = ["SCENARIO", "DESCRIPTION", "NODES", "RESPONDER_NODES", "NOISE_READINGS", "LINK_GAIN_TO_NODE1"]
    rows = []
    for key in keys:
        if key in metadata:
            rows.append("<tr><th>%s</th><td>%s</td></tr>" % (html_escape(key), html_escape(metadata[key])))
    if len(rows) == 0:
        return '<tr><th>Source</th><td>No metadata found.</td></tr>'
    return "\n".join(rows)


def write_html_report(result, path):
    metadata = result["metadata"]
    title = metadata.get("SCENARIO", os.path.basename(result["log_path"]))
    delay_svg = make_delay_svg(result["delay_points"])
    reply_svg = make_reply_bar_svg(result["reply_count_by_node"], result["responder_nodes"])
    table_rows = make_table_rows(result["delay_points"], 60)

    html = HTML_TEMPLATE % {
        "title": html_escape(title),
        "log_path": html_escape(result["log_path"]),
        "request_count": result["request_count"],
        "expected_reply_count": result["expected_reply_count"],
        "actual_reply_count": result["actual_reply_count"],
        "packet_reception_rate": result["packet_reception_rate"] * 100.0,
        "reply_request_ratio": result["reply_request_ratio"],
        "average_delay": result["average_delay"],
        "metadata_rows": make_metadata_rows(metadata),
        "legend": make_legend(result["responder_nodes"]),
        "delay_svg": delay_svg,
        "reply_svg": reply_svg,
        "table_rows": table_rows,
    }

    with open(path, "w") as f:
        f.write(html)


def make_comparison_bar(results, field, percent):
    width = 820
    height = 280
    pad_left = 70
    pad_right = 30
    pad_bottom = 62
    pad_top = 28
    plot_width = width - pad_left - pad_right
    plot_height = height - pad_top - pad_bottom
    values = [r[field] * 100.0 if percent else r[field] for r in results]
    max_value = max(values) if len(values) > 0 else 1
    if max_value <= 0:
        max_value = 1

    bar_width = min(88, plot_width / float(max(1, len(results)) * 2))
    pieces = [
        '<svg viewBox="0 0 %d %d">' % (width, height),
        '<rect x="0" y="0" width="%d" height="%d" fill="white"/>' % (width, height),
        '<line x1="%d" y1="%d" x2="%d" y2="%d" class="axis-line"/>' % (pad_left, height - pad_bottom, width - pad_right, height - pad_bottom),
        '<line x1="%d" y1="%d" x2="%d" y2="%d" class="axis-line"/>' % (pad_left, pad_top, pad_left, height - pad_bottom)
    ]

    for index, result in enumerate(results):
        value = values[index]
        x = pad_left + (index + 0.5) * (plot_width / float(len(results))) - bar_width / 2.0
        bar_height = (value / float(max_value)) * plot_height
        y = height - pad_bottom - bar_height
        label = result["metadata"].get("SCENARIO", os.path.basename(result["log_path"]))
        text_value = "%.2f%%" % value if percent else "%.2f" % value
        pieces.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" rx="4" fill="#2f6fed"/>' % (x, y, bar_width, bar_height))
        pieces.append('<text x="%.2f" y="%.2f" class="bar-value" text-anchor="middle">%s</text>' % (x + bar_width / 2.0, y - 8, text_value))
        pieces.append('<text x="%.2f" y="%d" class="axis-label" text-anchor="middle">%s</text>' % (x + bar_width / 2.0, height - 22, html_escape(label.replace("_", " "))))

    pieces.append('</svg>')
    return "\n".join(pieces)


def write_comparison_report(results, path):
    rows = []
    for result in results:
        scenario = result["metadata"].get("SCENARIO", os.path.basename(result["log_path"]))
        rows.append(
            "<tr><td>%s</td><td>%d</td><td>%d</td><td>%d</td><td>%.2f%%</td><td>%.2f ms</td></tr>"
            % (
                html_escape(scenario),
                result["request_count"],
                result["expected_reply_count"],
                result["actual_reply_count"],
                result["packet_reception_rate"] * 100.0,
                result["average_delay"],
            )
        )

    html = COMPARISON_TEMPLATE % {
        "success_chart": make_comparison_bar(results, "packet_reception_rate", True),
        "delay_chart": make_comparison_bar(results, "average_delay", False),
        "rows": "\n".join(rows),
    }

    with open(path, "w") as f:
        f.write(html)


HTML_TEMPLATE = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>TinyOS Request-Reply Simulation Report</title>
  <style>
    body { margin: 0; background: #f5f7fb; color: #1d2430; font-family: Arial, Helvetica, sans-serif; }
    header { background: #172033; color: #fff; padding: 28px 36px; }
    h1 { margin: 0 0 8px; font-size: 28px; font-weight: 700; }
    h2 { margin: 0 0 16px; font-size: 18px; }
    main { max-width: 1120px; margin: 24px auto 40px; padding: 0 20px; }
    .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-bottom: 18px; }
    .metric, .panel { background: #fff; border: 1px solid #dce3ef; border-radius: 8px; box-shadow: 0 1px 3px rgba(23, 32, 51, 0.06); }
    .metric { padding: 16px; }
    .metric-label { color: #5f6b7a; font-size: 13px; margin-bottom: 8px; }
    .metric-value { font-size: 26px; font-weight: 700; line-height: 1.1; }
    .panel { margin-top: 18px; padding: 18px; }
    .chart-row { display: grid; grid-template-columns: minmax(0, 1fr) minmax(360px, 0.7fr); gap: 18px; }
    .legend { display: flex; flex-wrap: wrap; gap: 12px 18px; color: #5f6b7a; font-size: 13px; margin-bottom: 8px; }
    .dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%%; margin-right: 6px; }
    .grid-line { stroke: #e6ebf2; stroke-width: 1; }
    .axis-line { stroke: #9aa6b5; stroke-width: 1.2; }
    .axis-label { fill: #5f6b7a; font-size: 12px; }
    .bar-value { fill: #1d2430; font-size: 13px; font-weight: 700; }
    table { width: 100%%; border-collapse: collapse; font-size: 14px; }
    th, td { border-bottom: 1px solid #e6ebf2; padding: 9px 10px; text-align: left; }
    th { color: #5f6b7a; font-weight: 700; background: #f9fbfe; }
    .empty-chart { padding: 32px; color: #5f6b7a; background: #fff; }
    @media (max-width: 850px) { header { padding: 22px 20px; } .chart-row { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <header>
    <h1>TinyOS Request-Reply Simulation Report</h1>
    <div>Scenario: %(title)s | Source: %(log_path)s</div>
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

    <section class="panel">
      <h2>Scenario Parameters</h2>
      <table><tbody>%(metadata_rows)s</tbody></table>
    </section>

    <section class="chart-row">
      <div class="panel">
        <h2>Reply Delay by Sequence</h2>
        <div class="legend">%(legend)s</div>
        %(delay_svg)s
      </div>
      <div class="panel">
        <h2>Replies by Node</h2>
        %(reply_svg)s
      </div>
    </section>

    <section class="panel">
      <h2>First 60 Reply Delay Records</h2>
      <table>
        <thead><tr><th>Sequence</th><th>Reply Node</th><th>Delay</th></tr></thead>
        <tbody>%(table_rows)s</tbody>
      </table>
    </section>
  </main>
</body>
</html>
"""


COMPARISON_TEMPLATE = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>TinyOS Scenario Comparison Report</title>
  <style>
    body { margin: 0; background: #f5f7fb; color: #1d2430; font-family: Arial, Helvetica, sans-serif; }
    header { background: #172033; color: #fff; padding: 28px 36px; }
    h1 { margin: 0 0 8px; font-size: 28px; font-weight: 700; }
    h2 { margin: 0 0 16px; font-size: 18px; }
    main { max-width: 1120px; margin: 24px auto 40px; padding: 0 20px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap: 18px; }
    .panel { background: #fff; border: 1px solid #dce3ef; border-radius: 8px; box-shadow: 0 1px 3px rgba(23, 32, 51, 0.06); margin-top: 18px; padding: 18px; }
    .axis-line { stroke: #9aa6b5; stroke-width: 1.2; }
    .axis-label { fill: #5f6b7a; font-size: 12px; }
    .bar-value { fill: #1d2430; font-size: 13px; font-weight: 700; }
    table { width: 100%%; border-collapse: collapse; font-size: 14px; }
    th, td { border-bottom: 1px solid #e6ebf2; padding: 9px 10px; text-align: left; }
    th { color: #5f6b7a; font-weight: 700; background: #f9fbfe; }
  </style>
</head>
<body>
  <header>
    <h1>TinyOS Scenario Comparison Report</h1>
    <div>Six-node request-reply simulation under different artificial noise settings</div>
  </header>
  <main>
    <section class="grid">
      <div class="panel"><h2>Reply Success Rate</h2>%(success_chart)s</div>
      <div class="panel"><h2>Average Delay</h2>%(delay_chart)s</div>
    </section>
    <section class="panel">
      <h2>Scenario Summary</h2>
      <table>
        <thead><tr><th>Scenario</th><th>Requests</th><th>Expected Replies</th><th>Actual Replies</th><th>Success Rate</th><th>Average Delay</th></tr></thead>
        <tbody>%(rows)s</tbody>
      </table>
    </section>
  </main>
</body>
</html>
"""


def print_result(result):
    print("===== Simulation Log Analysis: %s =====" % result["log_path"])
    print("Scenario: %s" % result["metadata"].get("SCENARIO", "unknown"))
    print("Request packets sent by node 1: %d" % result["request_count"])
    print("Expected reply packets: %d" % result["expected_reply_count"])
    print("Actual reply packets received by node 1: %d" % result["actual_reply_count"])
    for node in sorted(result["responder_nodes"]):
        print("Reply packets from node %d: %d" % (node, result["reply_count_by_node"].get(node, 0)))
    print("Packet reception rate: %.2f%%" % (result["packet_reception_rate"] * 100.0))
    print("Replies per request: %.2f" % result["reply_request_ratio"])
    print("Average delay: %.2f ms" % result["average_delay"])


def main():
    log_paths = sys.argv[1:]
    if len(log_paths) == 0:
        log_paths = ["log.txt"]

    results = []
    for log_path in log_paths:
        result = analyze_log(log_path)
        report_path = report_name_for_log(log_path)
        write_html_report(result, report_path)
        print_result(result)
        print("HTML report generated: %s" % report_path)
        results.append(result)

    if len(results) > 1:
        write_comparison_report(results, "comparison_report.html")
        print("Comparison report generated: comparison_report.html")


if __name__ == "__main__":
    main()
