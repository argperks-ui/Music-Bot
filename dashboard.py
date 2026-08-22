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
                <title>Music Bot Dashboard</title>
                <style>
                    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0d1117; color: #c9d1d9; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
                    .card {{ background-color: #161b22; padding: 30px; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.5); width: 380px; border: 1px solid #30363d; }}
                    h2 {{ margin-top: 0; color: #58a6ff; text-align: center; }}
                    .stat {{ margin: 15px 0; display: flex; justify-content: space-between; border-bottom: 1px solid #30363d; padding-bottom: 8px; }}
                    .label {{ font-weight: bold; color: #8b949e; }}
                    .value {{ color: #f0f6fc; text-align: right; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
                    .status-online {{ color: #3fb950; font-weight: bold; }}
                </style>
            </head>
            <body>
                <div class="card">
                    <h2>🎵 Music Bot Dashboard</h2>
                    <div class="stat"><span class="label">Status:</span> <span class="value status-online">{bot_status}</span></div>
                    <div class="stat"><span class="label">Now Playing:</span> <span class="value" title="{current_song}">{current_song}</span></div>
                    <div class="stat"><span class="label">Connected Servers:</span> <span class="value">{guild_count}</span></div>
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
    # Runs the web server in the background so it doesn't block the bot
    threading.Thread(target=run_server, daemon=True).start()