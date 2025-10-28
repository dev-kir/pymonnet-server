#!/usr/bin/env python3
from flask import Flask, request, jsonify
from datetime import datetime
import threading, subprocess, socket, time

app = Flask(__name__)
nodes = {}

# ============ Leader Detection ============
def is_swarm_leader():
    """Return True if this node is the current Docker Swarm leader."""
    try:
        result = subprocess.check_output(
            ["docker", "node", "ls", "--format", "{{.Hostname}} {{.ManagerStatus}}"]
        ).decode()
        hostname = socket.gethostname()
        for line in result.splitlines():
            if hostname in line and "Leader" in line:
                return True
        return False
    except Exception as e:
        print("Error checking leader:", e)
        return False
# ===========================================

@app.route('/metrics', methods=['POST'])
def receive_metrics():
    try:
        if not is_swarm_leader():
            return jsonify({"error": "this node is not leader"}), 403

        data = request.get_json(force=True)
        node = data.get('node')
        data['timestamp'] = datetime.now().isoformat(timespec='seconds')
        nodes[node] = data
        print(f"[{data['timestamp']}] {node}: {data}")
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"❌ Error receiving metrics: {e}")
        return jsonify({"error": str(e)}), 400

@app.route('/nodes', methods=['GET'])
def get_all_nodes():
    return jsonify(nodes), 200

@app.route('/')
def home():
    return "PyMonNet Leader Server Running", 200

def run_flask():
    app.run(host='0.0.0.0', port=6969)

if __name__ == '__main__':
    print("🌀 Checking if this node is Swarm leader...")
    while not is_swarm_leader():
        print("⏳ Waiting for this node to become leader...")
        time.sleep(5)
    print("🚀 This node is leader — starting PyMonNet server...")
    run_flask()
