#!/usr/bin/env python3
from flask import Flask, request, jsonify
from datetime import datetime
import subprocess, socket, time, sys

# Always flush logs immediately
sys.stdout.reconfigure(line_buffering=True)

app = Flask(__name__)
nodes = {}

# -----------------------------------------------------
# Leader detection helper
# -----------------------------------------------------
def is_swarm_leader():
    """Return True if this node is the current Docker Swarm leader."""
    try:
        result = subprocess.run(
            ["docker", "node", "ls", "--format", "{{.Hostname}} {{.ManagerStatus}}"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True
        )
        hostname = socket.gethostname()
        for line in result.stdout.splitlines():
            if hostname in line and "Leader" in line:
                return True
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Docker CLI error: {e.stderr.strip()}")
    except Exception as e:
        print(f"❌ Leader check failed: {e}")
    return False

# -----------------------------------------------------
# API endpoints
# -----------------------------------------------------
@app.route('/metrics', methods=['POST'])
def receive_metrics():
    if not is_swarm_leader():
        print("❌ Rejected /metrics — not the leader node.")
        return jsonify({"error": "this node is not leader"}), 403

    try:
        data = request.get_json(force=True)
        node = data.get('node', 'unknown')
        data['timestamp'] = datetime.now().isoformat(timespec='seconds')
        nodes[node] = data
        print(f"[{data['timestamp']}] ✅ {node}: {data}")
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"❌ Error receiving metrics: {e}")
        return jsonify({"error": str(e)}), 400


@app.route('/nodes', methods=['GET'])
def get_all_nodes():
    return jsonify(nodes), 200


@app.route('/')
def home():
    return f"PymonNet Leader Server Active on {socket.gethostname()}", 200

# -----------------------------------------------------
# Bootstrap leader wait loop
# -----------------------------------------------------
if __name__ == '__main__':
    print(f"🚀 Starting PyMonNet Manager Receiver on {socket.gethostname()}")
    while not is_swarm_leader():
        print("⏳ Waiting for this node to become leader...")
        time.sleep(5)
    print("✅ Node is Swarm leader — starting Flask server...")
    app.run(host='0.0.0.0', port=6969)
