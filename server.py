#!/usr/bin/env python3
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import subprocess, socket, time, json, os

app = Flask(__name__)

DATA_FILE = "nodes.json"
MAX_AGE_MIN = 10

# Load old data if exists
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        try:
            nodes = json.load(f)
        except json.JSONDecodeError:
            nodes = {}
else:
    nodes = {}

def save_nodes():
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(nodes, f, indent=2)
    except Exception as e:
        print(f"⚠️ Error saving JSON: {e}")

def cleanup_old_data():
    cutoff = datetime.now() - timedelta(minutes=MAX_AGE_MIN)
    for node, samples in list(nodes.items()):
        filtered = [s for s in samples if datetime.fromisoformat(s["timestamp"]) > cutoff]
        if filtered:
            nodes[node] = filtered
        else:
            nodes.pop(node, None)

@app.route('/metrics', methods=['POST'])
def receive_metrics():
    try:
        data = request.get_json(force=True)
        node = data.get('node')
        data['timestamp'] = datetime.now().isoformat(timespec='seconds')

        nodes.setdefault(node, []).append(data)
        cleanup_old_data()
        save_nodes()

        print(f"[{data['timestamp']}] ✅ Stored metric for {node}: {data}")
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"❌ Error receiving metrics: {e}")
        return jsonify({"error": str(e)}), 400

@app.route('/nodes', methods=['GET'])
def get_all_nodes():
    latest = {}
    for node, samples in nodes.items():
        if samples:
            latest[node] = samples[-1]
    return jsonify(latest), 200

@app.route('/nodes/history', methods=['GET'])
def get_all_history():
    return jsonify(nodes), 200

@app.route('/')
def home():
    return "✅ PyMonNet Leader Server running (JSON mode)", 200

if __name__ == "__main__":
    print("🚀 PyMonNet JSON Server starting on port 6969 ...")
    app.run(host="0.0.0.0", port=6969)
