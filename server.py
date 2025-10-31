#!/usr/bin/env python3
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import requests, os

# ================================
# PyMonNet Leader Server (InfluxDB + Realtime memory only)
# ================================
app = Flask(__name__)

# ---------------- CONFIGURATION ----------------
INFLUX_URL = "http://192.168.2.61:8086/api/v2/write?org=pymonnet&bucket=metrics&precision=s"
INFLUX_TOKEN = "1jEj4kVGBLMbkd24hIBLXnuWut967r4Tho1YD5lSCYBUJdB9lYZDFbDgpC2IC1OwdbjCHt8m3vhEI8VbNRfdCQ=="
HEADERS = {
    "Authorization": f"Token {INFLUX_TOKEN}",
    "Content-Type": "text/plain; charset=utf-8"
}
MAX_AGE_MIN = 5  # keep data in memory for last 5 minutes
# ------------------------------------------------

nodes = {}  # in-memory only (no file writes)

def cleanup_old_data():
    """Remove samples older than MAX_AGE_MIN."""
    cutoff = datetime.now() - timedelta(minutes=MAX_AGE_MIN)
    for node, samples in list(nodes.items()):
        filtered = [s for s in samples if datetime.fromisoformat(s["timestamp"]) > cutoff]
        if filtered:
            nodes[node] = filtered
        else:
            nodes.pop(node, None)


# ---------------- API ENDPOINTS ----------------
@app.route("/metrics", methods=["POST"])
def receive_metrics():
    """Receive metrics from agents, store in memory, push to InfluxDB."""
    try:
        data = request.get_json(force=True)
        node = data.get("node", "unknown")
        role = data.get("role", "unknown")
        data["timestamp"] = datetime.now().isoformat(timespec="seconds")

        # keep in memory only
        nodes.setdefault(node, []).append(data)
        cleanup_old_data()

        # push to InfluxDB (add role as tag)
        cpu = round(float(data.get("cpu", 0) or 0), 2)
        mem = round(float(data.get("mem", 0) or 0), 2)
        net_in = round(float(data.get("net_in", 0) or 0), 4)
        net_out = round(float(data.get("net_out", 0) or 0), 4)

        line = (
            f"nodes,node={node},role={role} "
            f"cpu={cpu:.2f},mem={mem:.2f},"
            f"net_in={net_in:.4f},net_out={net_out:.4f} "
            f"{int(datetime.now().timestamp())}"
        )

        try:
            r = requests.post(INFLUX_URL, headers=HEADERS, data=line.encode(), timeout=3)
            if r.status_code != 204:
                print(f"⚠️ Influx write failed {r.status_code}: {r.text}")
        except Exception as e:
            print(f"⚠️ Failed to push to InfluxDB: {e}")

        print(f"[{data['timestamp']}] ✅ Metric stored + sent for {node} ({role})")
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print(f"❌ Error receiving metrics: {e}")
        return jsonify({"error": str(e)}), 400


@app.route("/nodes", methods=["GET"])
def get_all_nodes():
    """Return latest snapshot of each node."""
    latest = {n: s[-1] for n, s in nodes.items() if s}
    return jsonify(latest), 200


@app.route("/nodes/history", methods=["GET"])
def get_all_history():
    """Return last few minutes of in-memory history."""
    return jsonify(nodes), 200


@app.route("/")
def home():
    return "✅ PyMonNet Server → InfluxDB bridge active (memory mode, role tagging enabled)", 200
# ------------------------------------------------


if __name__ == "__main__":
    print("🚀 PyMonNet Server starting (memory + InfluxDB + role tags)...")
    app.run(host="0.0.0.0", port=6969)
