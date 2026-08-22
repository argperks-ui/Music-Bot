import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Shared state variables that bot.py can modify
bot_status = "Starting..."
current_song = "None"
guild_count = 0

class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            html_content = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Music Bot | Command Center</title>
                <meta http-equiv="refresh" content="5">
                <style>
                    :root {{
                        --bg-color: #05050a;
                        --card-bg: rgba(18, 18, 30, 0.7);
                        --border-color: rgba(255, 255, 255, 0.08);
                        --accent-color: #5865F2;
                        --accent-glow: rgba(88, 101, 242, 0.3);
                        --text-main: #f3f4f6;
                        --text-muted: #9ca3af;
                        --online-color: #10b981;
                    }}
                    
                    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
                    
                    body {{
                        font-family: 'Inter', system-ui, -apple-system, sans-serif;
                        background-color: var(--bg-color);
                        background-image: 
                            radial-gradient(circle at 10% 20%, rgba(88, 101, 242, 0.15) 0%, transparent 40%),
                            radial-gradient(circle at 90% 80%, rgba(16, 185, 129, 0.1) 0%, transparent 40%);
                        color: var(--text-main);
                        min-height: 100vh;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        overflow: hidden;
                    }}

                    .container {{
                        width: 100%;
                        max-width: 440px;
                        padding: 20px;
                    }}

                    .card {{
                        background: var(--card-bg);
                        backdrop-filter: blur(20px);
                        -webkit-backdrop-filter: blur(20px);
                        border: 1px solid var(--border-color);
                        border-radius: 20px;
                        padding: 35px;
                        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7),
                                    0 0 30px var(--accent-glow);
                        position: relative;
                        overflow: hidden;
                    }}

                    .card::before {{
                        content: '';
                        position: absolute;
                        top: 0; left: 0; right: 0;
                        height: 2px;
                        background: linear-gradient(90deg, #5865F2, #10b981, #5865F2);
                        background-size: 200% 100%;
                        animation: shimmer 4s linear infinite;
                    }}

                    @keyframes shimmer {{
                        0% {{ background-position: 200% 0; }}
                        100% {{ background-position: -200% 0; }}
                    }}

                    .header {{
                        display: flex;
                        align-items: center;
                        gap: 15px;
                        margin-bottom: 25px;
                    }}

                    .logo-icon {{
                        width: 48px;
                        height: 48px;
                        background: linear-gradient(135deg, #5865F2, #4752C4);
                        border-radius: 14px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-size: 24px;
                        box-shadow: 0 8px 16px rgba(88, 101, 242, 0.3);
                    }}

                    .title-group h1 {{
                        font-size: 1.25rem;
                        font-weight: 700;
                        letter-spacing: -0.025em;
                        color: #ffffff;
                    }}

                    .title-group p {{
                        font-size: 0.8rem;
                        color: var(--text-muted);
                    }}

                    .metrics-grid {{
                        display: flex;
                        flex-direction: column;
                        gap: 15px;
                    }}

                    .metric-box {{
                        background: rgba(255, 255, 255, 0.03);
                        border: 1px solid rgba(255, 255, 255, 0.05);
                        border-radius: 12px;
                        padding: 15px 18px;
                        display: flex;
                        align-items: center;
                        justify-content: space-between;
                        transition: transform 0.2s ease, background 0.2s ease;
                    }}

                    .metric-box:hover {{
                        background: rgba(255, 255, 255, 0.05);
                        transform: translateY(-2px);
                    }}

                    .metric-label {{
                        font-size: 0.85rem;
                        font-weight: 500;
                        color: var(--text-muted);
                        display: flex;
                        align-items: center;
                        gap: 8px;
                    }}

                    .metric-value {{
                        font-size: 0.95rem;
                        font-weight: 600;
                        color: #ffffff;
                        max-width: 200px;
                        overflow: hidden;
                        text-overflow: ellipsis;
                        white-space: nowrap;
                    }}

                    .status-badge {{
                        display: inline-flex;
                        align-items: center;
                        gap: 6px;
                        padding: 4px 10px;
                        border-radius: 20px;
                        font-size: 0.8rem;
                        font-weight: 600;
                        background: rgba(16, 185, 129, 0.1);
                        color: var(--online-color);
                        border: 1px solid rgba(16, 185, 129, 0.2);
                    }}

                    .pulse-dot {{
                        width: 8px;
                        height: 8px;
                        background-color: var(--online-color);
                        border-radius: 50%;
                        animation: pulse 1.5s infinite;
                    }}

                    @keyframes pulse {{
                        0% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }}
                        70% {{ transform: scale(1); box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }}
                        100% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }}
                    }}

                    .audio-bars {{
                        display: flex;
                        align-items: flex-end;
                        gap: 3px;
                        height: 14px;
                    }}

                    .bar {{
                        width: 3px;
                        background: var(--accent-color);
                        border-radius: 3px;
                        animation: bounce 1.2s ease infinite alternate;
                    }}

                    .bar:nth-child(2) {{ animation-delay: 0.2s; }}
                    .bar:nth-child(3) {{ animation-delay: 0.4s; }}

                    @keyframes bounce {{
                        0% {{ height: 4px; }}
                        100% {{ height: 14px; }}
                    }}

                    .footer-note {{
                        text-align: center;
                        margin-top: 20px;
                        font-size: 0.75rem;
                        color: var(--text-muted);
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="card">
                        <div class="header">
                            <div class="logo-icon">🎵</div>
                            <div class="title-group">
                                <h1>Music Bot Hub</h1>
                                <p>Live Telemetry & Control Panel</p>
                            </div>
                        </div>

                        <div class="metrics-grid">
                            <div class="metric-box">
                                <span class="metric-label">System Status</span>
                                <div class="status-badge">
                                    <div class="pulse-dot"></div>
                                    {bot_status}
                                </div>
                            </div>

                            <div class="metric-box">
                                <span class="metric-label">
                                    Now Playing
                                    <div class="audio-bars">
                                        <div class="bar"></div>
                                        <div class="bar"></div>
                                        <div class="bar"></div>
                                    </div>
                                </span>
                                <span class="metric-value" title="{current_song}">{current_song}</span>
                            </div>

                            <div class="metric-box">
                                <span class="metric-label">Connected Servers</span>
                                <span class="metric-value" style="color: var(--accent-color);">🌐 {guild_count} Guilds</span>
                            </div>
                        </div>

                        <div class="footer-note">
                            Auto-syncs every 5 seconds • Render Edge Node
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            self.wfile.write(html_content.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), DashboardHandler)
    server.serve_forever()

def start_dashboard():
    threading.Thread(target=run_server, daemon=True).start()