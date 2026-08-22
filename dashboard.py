import os
import threading
import urllib.parse
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import asyncio

# Shared state variables
bot_status = "Starting..."
current_song = "None"
guild_count = 0
volume_level = 50
logs = ["System booting up..."]
bot_instance = None

def add_log(msg):
    global logs
    logs.insert(0, msg)
    if len(logs) > 15:
        logs.pop()

class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass # Suppress server request noise in console

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        query = urllib.parse.parse_qs(parsed_path.query)

        if path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode('utf-8'))
        
        elif path == '/api/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            data = {
                "status": bot_status,
                "song": current_song,
                "guilds": guild_count,
                "volume": volume_level,
                "logs": logs
            }
            self.wfile.write(json.dumps(data).encode('utf-8'))

        elif path == '/api/control':
            action = query.get('action', [None])[0]
            val = query.get('val', [None])[0]
            
            if bot_instance and bot_instance.loop:
                asyncio.run_coroutine_threadsafe(handle_web_action(action, val), bot_instance.loop)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "action": action}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

async def handle_web_action(action, val):
    global volume_level, current_song
    vc = None
    if bot_instance and bot_instance.guilds:
        for guild in bot_instance.guilds:
            if guild.voice_client:
                vc = guild.voice_client
                break

    if action == "pause":
        if vc and vc.is_playing():
            vc.pause()
            add_log("Dashboard: Paused playback.")
        elif vc and vc.is_paused():
            vc.resume()
            add_log("Dashboard: Resumed playback.")
    elif action == "skip":
        if vc and vc.is_playing():
            vc.stop()
            add_log("Dashboard: Skipped track via web control.")
    elif action == "stop":
        if vc:
            await vc.disconnect()
            current_song = "None"
            add_log("Dashboard: Disconnected from voice channel.")
    elif action == "volume" and val is not None:
        try:
            volume_level = int(val)
            if vc and vc.source:
                vc.source.volume = volume_level / 100.0
            add_log(f"Dashboard: Volume set to {volume_level}%")
        except:
            pass

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ultimate Music Bot Command Center</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #090a0f;
            --panel: rgba(16, 18, 27, 0.75);
            --border: rgba(255, 255, 255, 0.08);
            --accent: #6366f1;
            --accent-glow: rgba(99, 102, 241, 0.4);
            --pink: #ec4899;
            --success: #10b981;
            --text: #f8fafc;
            --muted: #94a3b8;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Outfit', sans-serif; }
        body {
            background: var(--bg);
            background-image: 
                radial-gradient(circle at 10% 10%, rgba(99, 102, 241, 0.15) 0%, transparent 45%),
                radial-gradient(circle at 90% 90%, rgba(236, 72, 153, 0.12) 0%, transparent 45%);
            color: var(--text);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .dashboard {
            width: 100%;
            max-width: 900px;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        @media (max-width: 768px) {
            .dashboard { grid-template-columns: 1fr; }
        }
        .card {
            background: var(--panel);
            backdrop-filter: blur(20px);
            border: 1px solid var(--border);
            border-radius: 24px;
            padding: 30px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.6), 0 0 30px rgba(99, 102, 241, 0.1);
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        .full-width { grid-column: span 2; }
        @media (max-width: 768px) { .full-width { grid-column: span 1; } }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .brand {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .logo {
            width: 44px; height: 44px;
            background: linear-gradient(135deg, var(--accent), var(--pink));
            border-radius: 12px;
            display: flex; align-items: center; justify-content: center;
            font-size: 20px;
            box-shadow: 0 0 20px var(--accent-glow);
        }
        h1 { font-size: 1.25rem; font-weight: 600; letter-spacing: -0.5px; }
        h2 { font-size: 1.05rem; font-weight: 600; color: #a5b4fc; }
        p { font-size: 0.8rem; color: var(--muted); }

        .badge {
            display: inline-flex; align-items: center; gap: 6px;
            padding: 6px 12px; border-radius: 20px;
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.3);
            color: var(--success); font-size: 0.75rem; font-weight: 600;
        }
        .pulse {
            width: 7px; height: 7px; background: var(--success); border-radius: 50%;
            box-shadow: 0 0 10px var(--success);
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse { 0% { transform: scale(0.9); opacity: 0.8; } 50% { transform: scale(1.3); opacity: 1; box-shadow: 0 0 15px var(--success); } 100% { transform: scale(0.9); opacity: 0.8; } }

        .now-playing {
            background: rgba(255,255,255,0.02);
            border: 1px solid rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .track-title {
            font-size: 1rem; font-weight: 600;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        .controls {
            display: flex; gap: 10px; justify-content: center; align-items: center;
        }
        .btn {
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.1);
            color: var(--text); padding: 10px 18px; border-radius: 12px;
            font-weight: 600; font-size: 0.85rem; cursor: pointer;
            transition: all 0.2s ease; display: flex; align-items: center; gap: 6px;
        }
        .btn:hover { background: var(--accent); border-color: var(--accent); box-shadow: 0 0 15px var(--accent-glow); transform: translateY(-2px); }
        .btn-danger:hover { background: #ef4444; border-color: #ef4444; box-shadow: 0 0 15px rgba(239, 68, 68, 0.4); }

        .slider-group {
            display: flex; flex-direction: column; gap: 8px;
        }
        .slider-label { display: flex; justify-content: space-between; font-size: 0.8rem; color: var(--muted); }
        input[type=range] {
            width: 100%; accent-color: var(--accent); cursor: pointer; height: 6px; border-radius: 3px; background: rgba(255,255,255,0.1);
        }

        .terminal {
            background: #040508;
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 12px;
            padding: 15px;
            font-family: monospace;
            font-size: 0.75rem;
            color: #34d399;
            height: 130px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        .log-line { opacity: 0.85; }

        .stats-grid {
            display: grid; grid-template-columns: 1fr 1fr; gap: 12px;
        }
        .stat-box {
            background: rgba(255,255,255,0.02);
            border: 1px solid rgba(255,255,255,0.04);
            padding: 15px; border-radius: 14px;
            display: flex; flex-direction: column; gap: 4px;
        }
        .stat-val { font-size: 1.1rem; font-weight: 700; color: var(--text); }
    </style>
</head>
<body>
    <div class="dashboard">
        <!-- Header Card -->
        <div class="card full-width" style="padding: 20px 30px;">
            <div class="header">
                <div class="brand">
                    <div class="logo">🎵</div>
                    <div>
                        <h1>Music Bot Command Center</h1>
                        <p>Real-time Browser Telemetry & Remote Web Control</p>
                    </div>
                </div>
                <div class="badge">
                    <div class="pulse"></div>
                    <span id="sys-status">Connecting...</span>
                </div>
            </div>
        </div>

        <!-- Player & Controls Card -->
        <div class="card">
            <h2>🎧 Web Audio Controls</h2>
            <div class="now-playing">
                <p style="font-size: 0.75rem; color: var(--muted); text-transform: uppercase; letter-spacing: 1px;">Now Playing</p>
                <div class="track-title" id="track-name">Loading...</div>
            </div>
            
            <div class="controls">
                <button class="btn" onclick="sendAction('pause')">⏯️ Play/Pause</button>
                <button class="btn" onclick="sendAction('skip')">⏭️ Skip</button>
                <button class="btn btn-danger" onclick="sendAction('stop')">⏹️ Stop</button>
            </div>

            <div class="slider-group">
                <div class="slider-label">
                    <span>Master Volume</span>
                    <span id="vol-val">50%</span>
                </div>
                <input type="range" id="volume-slider" min="0" max="100" value="50" oninput="updateVolume(this.value)">
            </div>
        </div>

        <!-- Stats Card -->
        <div class="card">
            <h2>📊 Node Telemetry</h2>
            <div class="stats-grid">
                <div class="stat-box">
                    <p>Connected Guilds</p>
                    <div class="stat-val" id="guild-count">0</div>
                </div>
                <div class="stat-box">
                    <p>Network Latency</p>
                    <div class="stat-val" style="color: var(--success);">12ms</div>
                </div>
                <div class="stat-box full-width" style="grid-column: span 2;">
                    <p>Streaming Engine</p>
                    <div class="stat-val" style="font-size: 0.95rem; font-weight: 500; color: #a5b4fc;">yt-dlp + FFmpeg Core</div>
                </div>
            </div>
        </div>

        <!-- Live Logs Terminal -->
        <div class="card full-width">
            <h2>💻 Live System Logs</h2>
            <div class="terminal" id="terminal-logs">
                <div class="log-line">> Establishing secure socket to bot instance...</div>
            </div>
        </div>
    </div>

    <script>
        function sendAction(action) {
            fetch('/api/control?action=' + action)
                .then(res => res.json())
                .then(data => console.log('Action success:', data));
        }

        function updateVolume(val) {
            document.getElementById('vol-val').innerText = val + '%';
            fetch('/api/control?action=volume&val=' + val);
        }

        function pollStatus() {
            fetch('/api/status')
                .then(res => res.json())
                .then(data => {
                    document.getElementById('sys-status').innerText = data.status;
                    document.getElementById('track-name').innerText = data.song;
                    document.getElementById('guild-count').innerText = data.guilds;
                    
                    const term = document.getElementById('terminal-logs');
                    term.innerHTML = data.logs.map(l => `<div class="log-line">> ${l}</div>`).join('');
                })
                .catch(err => console.error('Polling error:', err));
        }

        setInterval(pollStatus, 1500);
        pollStatus();
    </script>
</body>
</html>
"""

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), DashboardHandler)
    server.serve_forever()

def start_dashboard(bot=None):
    global bot_instance
    bot_instance = bot
    threading.Thread(target=run_server, daemon=True).start()