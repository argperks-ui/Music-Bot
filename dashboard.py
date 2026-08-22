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
logs = ["System core initialized..."]
bot_instance = None

def add_log(msg):
    global logs
    logs.insert(0, msg)
    if len(logs) > 30:
        logs.pop()

class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass # Suppress terminal log spam

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
            
            guild_names = []
            if bot_instance and bot_instance.guilds:
                guild_names = [g.name for g in bot_instance.guilds]

            data = {
                "status": bot_status,
                "song": current_song,
                "guilds": guild_count,
                "guild_names": guild_names,
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
            add_log("Dashboard Web Action: Paused playback.")
        elif vc and vc.is_paused():
            vc.resume()
            add_log("Dashboard Web Action: Resumed playback.")
    elif action == "skip":
        if vc and vc.is_playing():
            vc.stop()
            add_log("Dashboard Web Action: Skipped current track.")
    elif action == "stop":
        if vc:
            await vc.disconnect()
            current_song = "None"
            add_log("Dashboard Web Action: Disconnected from voice channel.")
    elif action == "volume" and val is not None:
        try:
            volume_level = int(val)
            if vc and vc.source:
                vc.source.volume = volume_level / 100.0
            add_log(f"Dashboard Web Action: Volume adjusted to {volume_level}%")
        except:
            pass

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nexus Music Bot | Ultimate Command Center</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #030407;
            --panel: rgba(13, 15, 25, 0.85);
            --border: rgba(255, 255, 255, 0.08);
            --accent: #6366f1;
            --accent-glow: rgba(99, 102, 241, 0.35);
            --pink: #f43f5e;
            --success: #10b981;
            --text: #f8fafc;
            --muted: #94a3b8;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Plus Jakarta Sans', sans-serif; }
        body {
            background: var(--bg);
            background-image: 
                radial-gradient(circle at 15% 15%, rgba(99, 102, 241, 0.12) 0%, transparent 40%),
                radial-gradient(circle at 85% 85%, rgba(244, 63, 94, 0.1) 0%, transparent 40%);
            color: var(--text);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .wrapper {
            width: 100%;
            max-width: 950px;
            background: var(--panel);
            backdrop-filter: blur(25px);
            border: 1px solid var(--border);
            border-radius: 28px;
            box-shadow: 0 25px 60px rgba(0,0,0,0.7), 0 0 40px rgba(99, 102, 241, 0.15);
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }
        
        /* Top Navigation Header */
        .header {
            padding: 25px 35px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: rgba(255, 255, 255, 0.01);
        }
        .brand { display: flex; align-items: center; gap: 14px; }
        .logo {
            width: 48px; height: 48px;
            background: linear-gradient(135deg, var(--accent), var(--pink));
            border-radius: 14px;
            display: flex; align-items: center; justify-content: center;
            font-size: 22px;
            box-shadow: 0 0 20px var(--accent-glow);
        }
        .brand h1 { font-size: 1.3rem; font-weight: 700; letter-spacing: -0.5px; }
        .brand p { font-size: 0.8rem; color: var(--muted); }

        .status-badge {
            display: inline-flex; align-items: center; gap: 8px;
            padding: 8px 16px; border-radius: 30px;
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.3);
            color: var(--success); font-size: 0.8rem; font-weight: 600;
        }
        .pulse {
            width: 8px; height: 8px; background: var(--success); border-radius: 50%;
            box-shadow: 0 0 10px var(--success);
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse { 0% { transform: scale(0.9); opacity: 0.8; } 50% { transform: scale(1.4); opacity: 1; box-shadow: 0 0 15px var(--success); } 100% { transform: scale(0.9); opacity: 0.8; } }

        /* Tabs Bar */
        .tabs {
            display: flex;
            gap: 10px;
            padding: 15px 35px;
            background: rgba(0,0,0,0.2);
            border-bottom: 1px solid var(--border);
        }
        .tab-btn {
            background: transparent;
            border: none;
            color: var(--muted);
            padding: 10px 20px;
            border-radius: 12px;
            font-weight: 600;
            font-size: 0.85rem;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .tab-btn:hover { color: var(--text); background: rgba(255,255,255,0.04); }
        .tab-btn.active { color: #fff; background: var(--accent); box-shadow: 0 0 15px var(--accent-glow); }

        /* Tab Content Containers */
        .tab-content { display: none; padding: 35px; animation: fadeIn 0.3s ease; }
        .tab-content.active { display: grid; grid-template-columns: 1fr 1fr; gap: 25px; }
        .tab-content.single-col { display: none; padding: 35px; }
        .tab-content.single-col.active { display: block; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }

        .card {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 20px;
            padding: 25px;
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        .full-width { grid-column: span 2; }
        
        h2 { font-size: 1.1rem; font-weight: 600; color: #a5b4fc; margin-bottom: 5px; }
        
        /* Interactive Controls */
        .now-playing-box {
            background: rgba(99, 102, 241, 0.05);
            border: 1px solid rgba(99, 102, 241, 0.2);
            border-radius: 14px;
            padding: 20px;
            display: flex; flex-direction: column; gap: 6px;
        }
        .track-title { font-size: 1.05rem; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #fff; }
        
        .controls-row { display: flex; gap: 12px; justify-content: center; }
        .btn {
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.1);
            color: var(--text); padding: 12px 20px; border-radius: 14px;
            font-weight: 600; font-size: 0.85rem; cursor: pointer;
            transition: all 0.2s ease; display: flex; align-items: center; gap: 8px; flex: 1; justify-content: center;
        }
        .btn:hover { background: var(--accent); border-color: var(--accent); box-shadow: 0 0 15px var(--accent-glow); transform: translateY(-2px); }
        .btn-danger:hover { background: var(--pink); border-color: var(--pink); box-shadow: 0 0 15px rgba(244, 63, 94, 0.4); }

        .slider-box { display: flex; flex-direction: column; gap: 8px; }
        .slider-info { display: flex; justify-content: server; justify-content: space-between; font-size: 0.82rem; color: var(--muted); }
        input[type=range] { width: 100%; accent-color: var(--accent); cursor: pointer; height: 6px; border-radius: 3px; background: rgba(255,255,255,0.1); }

        /* Terminal Logs */
        .terminal {
            background: #020305;
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 16px;
            padding: 20px;
            font-family: monospace;
            font-size: 0.8rem;
            color: #34d399;
            height: 280px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .log-line { opacity: 0.85; border-left: 2px solid var(--success); padding-left: 8px; }

        /* Guilds List */
        .guild-list { display: flex; flex-direction: column; gap: 10px; max-height: 250px; overflow-y: auto; }
        .guild-item {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.05);
            padding: 12px 18px; border-radius: 12px;
            display: flex; justify-content: space-between; align-items: center;
            font-size: 0.9rem; font-weight: 500;
        }
    </style>
</head>
<body>
    <div class="wrapper">
        <!-- Header -->
        <div class="header">
            <div class="brand">
                <div class="logo">⚡</div>
                <div>
                    <h1>Nexus Command Center</h1>
                    <p>Advanced Discord Bot Telemetry & Control Suite</p>
                </div>
            </div>
            <div class="status-badge">
                <div class="pulse"></div>
                <span id="sys-status">Connecting...</span>
            </div>
        </div>

        <!-- Navigation Tabs -->
        <div class="tabs">
            <button class="tab-btn active" onclick="switchTab('overview', event)">📊 Overview</button>
            <button class="tab-btn" onclick="switchTab('control', event)">🎧 Remote & Audio</button>
            <button class="tab-btn" onclick="switchTab('guilds', event)">🌐 Servers</button>
            <button class="tab-btn" onclick="switchTab('terminal', event)">💻 System Logs</button>
        </div>

        <!-- TAB 1: OVERVIEW -->
        <div id="overview" class="tab-content active">
            <div class="card">
                <h2>Node Status</h2>
                <p style="font-size: 0.9rem; color: var(--muted);">Running secure container on Render Cloud infrastructure with active FFmpeg piping and yt-dlp stream dispatchers.</p>
                <div style="margin-top: 10px; display: flex; gap: 15px;">
                    <div style="background: rgba(255,255,255,0.03); padding: 15px; border-radius: 12px; flex: 1;">
                        <span style="font-size: 0.75rem; color: var(--muted);">CONNECTED GUILDS</span>
                        <div id="stat-guilds" style="font-size: 1.4rem; font-weight: 700; color: #fff; margin-top: 4px;">0</div>
                    </div>
                    <div style="background: rgba(255,255,255,0.03); padding: 15px; border-radius: 12px; flex: 1;">
                        <span style="font-size: 0.75rem; color: var(--muted);">LATENCY</span>
                        <div style="font-size: 1.4rem; font-weight: 700; color: var(--success); margin-top: 4px;">14ms</div>
                    </div>
                </div>
            </div>
            <div class="card">
                <h2>Active Playback State</h2>
                <div class="now-playing-box">
                    <span style="font-size: 0.7rem; color: var(--muted); text-transform: uppercase; letter-spacing: 1px;">Currently Streaming</span>
                    <div class="track-title" id="overview-song">None</div>
                </div>
                <p style="font-size: 0.8rem; color: var(--muted);">Use slash commands in Discord or switch to the Remote tab to control audio streams instantly.</p>
            </div>
        </div>

        <!-- TAB 2: REMOTE CONTROL -->
        <div id="control" class="tab-content">
            <div class="card full-width">
                <h2>Web Audio Control Deck</h2>
                <div class="now-playing-box" style="margin-bottom: 10px;">
                    <span style="font-size: 0.7rem; color: var(--muted); text-transform: uppercase;">Active Track</span>
                    <div class="track-title" id="control-song">None</div>
                </div>
                
                <div class="controls-row">
                    <button class="btn" onclick="sendAction('pause')">⏯️ Play / Pause</button>
                    <button class="btn" onclick="sendAction('skip')">⏭️ Skip Track</button>
                    <button class="btn btn-danger" onclick="sendAction('stop')">⏹️ Disconnect Bot</button>
                </div>

                <div class="slider-box" style="margin-top: 15px;">
                    <div class="slider-info">
                        <span>Master Output Volume</span>
                        <span id="vol-text">50%</span>
                    </div>
                    <input type="range" id="vol-slider" min="0" max="100" value="50" oninput="setVolume(this.value)">
                </div>
            </div>
        </div>

        <!-- TAB 3: SERVERS -->
        <div id="guilds" class="tab-content">
            <div class="card full-width">
                <h2>Connected Discord Guilds</h2>
                <p style="font-size: 0.82rem; color: var(--muted);">Servers where this bot instance is currently authenticated and active:</p>
                <div class="guild-list" id="guild-container">
                    <div class="guild-item"><span>Loading servers...</span></div>
                </div>
            </div>
        </div>

        <!-- TAB 4: TERMINAL LOGS -->
        <div id="terminal" class="tab-content single-col">
            <div class="card">
                <h2>Live Execution Terminal</h2>
                <div class="terminal" id="terminal-logs">
                    <div class="log-line">> Connecting to system socket...</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        function switchTab(tabId, evt) {
            document.querySelectorAll('.tab-content, .tab-content.single-col').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
            
            document.getElementById(tabId).classList.add('active');
            evt.currentTarget.classList.add('active');
        }

        function sendAction(action) {
            fetch('/api/control?action=' + action).then(res => res.json());
        }

        function setVolume(val) {
            document.getElementById('vol-text').innerText = val + '%';
            fetch('/api/control?action=volume&val=' + val);
        }

        function updateData() {
            fetch('/api/status')
                .then(res => res.json())
                .then(data => {
                    document.getElementById('sys-status').innerText = data.status;
                    document.getElementById('overview-song').innerText = data.song;
                    document.getElementById('control-song').innerText = data.song;
                    document.getElementById('stat-guilds').innerText = data.guilds;

                    // Update Guilds list
                    const container = document.getElementById('guild-container');
                    if (data.guild_names.length > 0) {
                        container.innerHTML = data.guild_names.map(g => `<div class="guild-item"><span>🛡️ ${g}</span><span style="color:var(--success); font-size:0.75rem;">Active</span></div>`).join('');
                    } else {
                        container.innerHTML = '<div class="guild-item"><span>No connected servers found</span></div>';
                    }

                    // Update logs
                    const term = document.getElementById('terminal-logs');
                    term.innerHTML = data.logs.map(l => `<div class="log-line">> ${l}</div>`).join('');
                })
                .catch(err => console.error('Sync error:', err));
        }

        setInterval(updateData, 1500);
        updateData();
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