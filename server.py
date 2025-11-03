#!/usr/bin/env python3
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import math
import requests, os

app = Flask(__name__)

# ---------------- CONFIGURATION ----------------
INFLUX_URL = "http://192.168.2.61:8086/api/v2/write?org=pymonnet&bucket=metrics&precision=s"
INFLUX_TOKEN = "ks0cnTPipvphipQIuKT7w7gHAYMZx4GoxvN_3vSGAQd7o1UmcKD64WPYiIFwEteNnRuohJYqsj_4qO5Nr9yvMw=="

HEADERS = {
    "Authorization": f"Token {INFLUX_TOKEN}",
    "Content-Type": "text/plain; charset=utf-8"
}
MAX_AGE_MIN = 5  # keep node history in memory for last 5 minutes

# In-memory data
nodes = {}        # { node: [ { cpu, mem, ... } ] }
containers = {}   # { node: [ { container, cpu, mem, net_in, net_out } ] }  ✅ new
# ------------------------------------------------


def _escape_tag(value):
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace(" ", "\\ ")
        .replace(",", "\\,")
        .replace("=", "\\=")
    )


def _clean_metric(value, decimals):
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = 0.0
    if not math.isfinite(numeric):
        numeric = 0.0
    return round(numeric, decimals)


def cleanup_old_data():
    """Remove node samples older than MAX_AGE_MIN."""
    cutoff = datetime.now() - timedelta(minutes=MAX_AGE_MIN)
    for node, samples in list(nodes.items()):
        filtered = [s for s in samples if datetime.fromisoformat(s["timestamp"]) > cutoff]
        if filtered:
            nodes[node] = filtered
        else:
            nodes.pop(node, None)
    # Containers persist as "latest known" — no cleanup needed


# ---------------- API ENDPOINTS ----------------
@app.route("/metrics", methods=["POST"])
def receive_metrics():
    """Receive node-level metrics from agents."""
    try:
        data = request.get_json(force=True)
        node = data.get("node", "unknown")
        role = data.get("role", "unknown")
        data["timestamp"] = datetime.now().isoformat(timespec="seconds")

        # store in memory
        nodes.setdefault(node, []).append(data)
        cleanup_old_data()

        # InfluxDB (optional, background metric)
        cpu = _clean_metric(data.get("cpu", 0), 2)
        mem = _clean_metric(data.get("mem", 0), 2)
        net_in = _clean_metric(data.get("net_in", 0), 4)
        net_out = _clean_metric(data.get("net_out", 0), 4)
        status = data.get("status", "unknown")

        tag_node = _escape_tag(node)
        tag_role = _escape_tag(role)
        status_field = str(status).replace("\\", "\\\\").replace("\"", "\\\"")

        line = (
            f"nodes,node={tag_node},role={tag_role} "
            f"cpu={cpu:.2f},mem={mem:.2f},"
            f"net_in={net_in:.4f},net_out={net_out:.4f},"
            f"status=\"{status_field}\" "
            f"{int(datetime.now().timestamp())}"
        )

        try:
            r = requests.post(INFLUX_URL, headers=HEADERS, data=line.encode(), timeout=2)
            if r.status_code != 204:
                print(f"⚠️ Influx write failed {r.status_code}: {r.text}")
        except Exception as e:
            print(f"⚠️ Failed to push to InfluxDB: {e}")

        print(f"[{data['timestamp']}] ✅ Node metric stored for {node}")
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print(f"❌ Error receiving metrics: {e}")
        return jsonify({"error": str(e)}), 400


@app.route("/container-metrics", methods=["POST"])
def receive_container_metrics():
    """Receive detailed per-container metrics when node is under stress."""
    try:
        data_list = request.get_json(force=True)
        if not isinstance(data_list, list):
            data_list = [data_list]

        latest_by_node = {}

        for data in data_list:
            node = data.get("node", "unknown")
            container_name = data.get("container", "unknown")
            container_id = data.get("container_id", "unknown")

            entry = {
                "container": container_name,
                "container_id": container_id,
                "cpu": _clean_metric(data.get("cpu", 0), 2),
                "mem": _clean_metric(data.get("mem", 0), 2),
                "net_in": _clean_metric(data.get("net_in", 0), 3),
                "net_out": _clean_metric(data.get("net_out", 0), 3),
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            }

            latest_by_node.setdefault(node, []).append(entry)

        # ✅ store in memory
        for node, items in latest_by_node.items():
            containers[node] = items

        print(f"[{datetime.now().isoformat(timespec='seconds')}] ✅ Container metrics updated for {list(latest_by_node.keys())}")
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print(f"❌ Error in /container-metrics: {e}")
        return jsonify({"error": str(e)}), 400


@app.route("/nodes", methods=["GET"])
def get_all_nodes():
    """Return latest node snapshot including container details."""
    latest = {n: s[-1] for n, s in nodes.items() if s}
    for node in latest.keys():
        if node in containers:
            latest[node]["containers"] = containers[node]
    return jsonify(latest), 200


@app.route("/nodes/history", methods=["GET"])
def get_all_history():
    """Return last few minutes of in-memory node history."""
    return jsonify(nodes), 200


@app.route("/")
def home():
    return "✅ PyMonNet Server → memory + role tagging active", 200


if __name__ == "__main__":
    print("🚀 PyMonNet Server starting (memory + InfluxDB + container cache)...")
    app.run(host="0.0.0.0", port=6969)
