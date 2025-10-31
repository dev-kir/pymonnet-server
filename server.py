#!/usr/bin/env python3
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import requests, json, os

# ================================
# PyMonNet Leader Server (InfluxDB-enabled)
# ================================
app = Flask(__name__)

# ---------------- CONFIGURATION ----------------
DATA_FILE = "nodes.json"                # local short-term storage
MAX_AGE_MIN = 10                        # keep only last 10 minutes in JSON
INFLUX_URL = "http://192.168.2.61:8086/api/v2/write?org=pymonnet&bucket=metrics&precision=s"
INFLUX_TOKEN = "1jEj4kVGBLMbkd24hIBLXnuWut967r4Tho1YD5lSCYBUJdB9lYZDFbDgpC2IC1OwdbjCHt8m3vhEI8VbNRfdCQ=="
HEADERS = {
    "Authorization": f"Token {INFLUX_TOKEN}",
    "Content-Type": "text/plain; charset=utf-8"
}
# ------------------------------------------------

# Load cached data
nodes = {}
if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE) as f:
            nodes = json.load(f)
    except json.JSONDecodeError:
        nodes = {}

def save_nodes():
    """Persist recent metrics to local JSON."""
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(nodes, f, indent=2)
    except Exception as e:
        print(f"⚠️ Error saving JSON: {e}")

def cleanup_old_data():
    """Remove old samples beyond MAX_AGE_MIN."""
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
    """Receive metrics from PyMonNet agents and forward to InfluxDB."""
    try:
        data = request.get_json(force=True)
        node = data.get("node", "unknown")
        data["timestamp"] = datetime.now().isoformat(timespec="seconds")

        # Store locally for short-term dashboard
        nodes.setdefault(node, []).append(data)
        cleanup_old_data()
        save_nodes()

        # Prepare Influx line protocol
        line = (
            f"nodes,node={node} "
            f"cpu={data.get('cpu',0)},mem={data.get('mem',0)},"
            f"net_in={data.get('net_in',0)},net_out={data.get('net_out',0)} "
            f"{int(datetime.now().timestamp())}"
        )

        # Send to InfluxDB
        try:
            r = requests.post(INFLUX_URL, headers=HEADERS, data=line.encode(), timeout=3)
            if r.status_code != 204:
                print(f"⚠️ Influx write failed {r.status_code}: {r.text}")
        except Exception as e:
            print(f"⚠️ Failed to push to InfluxDB: {e}")

        print(f"[{data['timestamp']}] ✅ Stored + sent metric for {node}")
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print(f"❌ Error receiving metrics: {e}")
        return jsonify({"error": str(e)}), 400


@app.route("/nodes", methods=["GET"])
def get_all_nodes():
    """Return the latest snapshot of all nodes."""
    latest = {n: s[-1] for n, s in nodes.items() if s}
    return jsonify(latest), 200


@app.route("/nodes/history", methods=["GET"])
def get_all_history():
    """Return short-term history (last 10 minutes)."""
    return jsonify(nodes), 200


@app.route("/")
def home():
    return "✅ PyMonNet Server → InfluxDB bridge active", 200
# ------------------------------------------------


if __name__ == "__main__":
    print("🚀 PyMonNet Server starting with InfluxDB forwarding...")
    app.run(host="0.0.0.0", port=6969)
