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

@app.route('/dashboard')
def dashboard():
    """Simple realtime dashboard (auto refreshes every 5s)."""
    return """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>PyMonNet Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    body { font-family: sans-serif; background: #111; color: #eee; }
    canvas { max-width: 800px; margin: 20px auto; display: block; }
    h2 { text-align: center; }
  </style>
</head>
<body>
  <h2>📊 PyMonNet Realtime Dashboard</h2>
  <div id="charts"></div>

  <script>
    async function fetchData() {
      const res = await fetch('/nodes/history');
      return await res.json();
    }

    async function renderCharts() {
      const data = await fetchData();
      const chartsDiv = document.getElementById('charts');
      chartsDiv.innerHTML = '';  // clear old charts

      for (const [node, samples] of Object.entries(data)) {
        const labels = samples.map(s => s.timestamp.split('T')[1]);
        const cpu = samples.map(s => s.cpu);
        const mem = samples.map(s => s.mem);

        const canvas = document.createElement('canvas');
        chartsDiv.appendChild(canvas);

        new Chart(canvas, {
          type: 'line',
          data: {
            labels: labels,
            datasets: [
              { label: node + ' CPU %', data: cpu, borderColor: 'red', fill: false },
              { label: node + ' MEM %', data: mem, borderColor: 'cyan', fill: false }
            ]
          },
          options: {
            responsive: true,
            scales: { y: { beginAtZero: true, max: 100 } },
            plugins: { legend: { labels: { color: '#eee' } } }
          }
        });
      }
    }

    renderCharts();
    setInterval(renderCharts, 5000); // refresh every 5s
  </script>
</body>
</html>
    """

if __name__ == "__main__":
    print("🚀 PyMonNet JSON Server starting on port 6969 ...")
    app.run(host="0.0.0.0", port=6969)
