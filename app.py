# app.py
"""
Volcano Monitoring Center — Main Application Entry Point
Menggabungkan seluruh modul API, Database, Monitoring Scraper, Weather, Telegram Notifier, SocketIO WebSocket, dan UI Dashboard.
"""
import sys
import os
import json
import time
import traceback
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
from flask import Flask, render_template, send_from_directory, jsonify, Response

from database.db import init_db, SNAPSHOT_DIR
from database.queries import get_latest_status
from monitoring.scheduler import start_monitoring_scheduler
from utils.level_mapper import GUNUNG_TARGET
from telegram.bot import is_telegram_configured

try:
    from flask_socketio import SocketIO, emit
    HAS_SOCKETIO = True
except ImportError:
    HAS_SOCKETIO = False

# Blueprints
from api.status_routes import status_bp
from api.kubah_lava_routes import kubah_lava_bp
from api.gempa_routes import gempa_bp
from api.gas_routes import gas_bp
from api.awan_panas_routes import awan_panas_bp
from api.cctv_routes import cctv_bp
from api.panduan_routes import panduan_bp
from api.statistik_routes import statistik_bp
from api.peringatan_routes import peringatan_bp
from api.auth_routes import auth_bp
from api.weather_routes import weather_bp

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.environ.get("VOLCANO_APP_SECRET", "volcano-secret-key-prod-2026")
app.config.update(SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_HTTPONLY=True)

if HAS_SOCKETIO:
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode="gevent" if os.name != "nt" else "threading")

    @socketio.on("connect")
    def handle_connect():
        emit("connected", {"message": "WebSocket terhubung ke Volcano Monitoring Center"})
else:
    socketio = None

# Register Blueprints
app.register_blueprint(status_bp)
app.register_blueprint(kubah_lava_bp)
app.register_blueprint(gempa_bp)
app.register_blueprint(gas_bp)
app.register_blueprint(awan_panas_bp)
app.register_blueprint(cctv_bp)
app.register_blueprint(panduan_bp)
app.register_blueprint(statistik_bp)
app.register_blueprint(peringatan_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(weather_bp)

# Root Frontend Route
@app.route("/")
def index():
    return render_template("index.html")

# Dedicated Edukasi Route
@app.route("/edukasi")
def edukasi():
    return render_template("edukasi.html")

# Serve CCTV Snapshots
@app.route("/snapshots/<path:filename>")
def serve_snapshot(filename):
    return send_from_directory(SNAPSHOT_DIR, filename)

# Server-Sent Events (SSE) Stream Fallback
@app.route("/api/stream")
def api_stream():
    def event_stream():
        last_data = {}
        while True:
            try:
                current = {}
                for slug in GUNUNG_TARGET:
                    status = get_latest_status(slug)
                    current[slug] = status

                if current != last_data:
                    payload = json.dumps({
                        "gunung": current,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }, ensure_ascii=False)
                    yield f"data: {payload}\n\n"
                    last_data = {k: (dict(v) if v else None) for k, v in current.items()}
                else:
                    yield f": heartbeat\n\n"

                time.sleep(5)
            except GeneratorExit:
                break
            except Exception as e:
                yield f"data: {{\"error\": \"{e}\"}}\n\n"
                time.sleep(10)

    return Response(
        event_stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )

@app.errorhandler(Exception)
def handle_global_exception(e):
    traceback.print_exc()
    if request.path.startswith("/api/"):
        return jsonify({"error": str(e), "path": request.path}), 500
    return render_template("index.html"), 200

if __name__ == "__main__":
    init_db()
    start_monitoring_scheduler()

    print("=" * 60)
    print(" [VOLCANO] Indonesia Volcano Monitoring Center (2.0)")
    print(f" [TELEGRAM] Alert System: {'AKTIF' if is_telegram_configured() else 'NONAKTIF'}")
    print(" [URL] Buka browser di: http://localhost:5000")
    print("=" * 60)
    
    port = int(os.environ.get("PORT", 5000))
    if socketio:
        socketio.run(app, host="0.0.0.0", port=port, debug=False, allow_unsafe_werkzeug=True)
    else:
        app.run(host="0.0.0.0", port=port, debug=False)