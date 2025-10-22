#!/usr/bin/env python3
from flask import Flask, request, jsonify
from datetime import datetime
import threading

app = Flask(__name__)

# in-memory store for latest metrics per node
nodes = {}

@app.route('/metrics', methods=['POST'])
def receive_metrics():
    try:
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
    return "PymonNet Manager Receiver Running", 200

def run_flask():
    app.run(host='0.0.0.0', port=6969)

if __name__ == '__main__':
    print("🚀 Starting Manager Receiver on port 6969 ...")
    run_flask()
