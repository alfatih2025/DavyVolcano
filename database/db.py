# database/db.py
"""
Koneksi dan Inisialisasi Database SQLite volcano.db
Mendukung tabel antrean Telegram offline dan cache cuaca Open Meteo.
"""
import os
import sqlite3

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.environ.get("DATA_DIR", BASE_DIR)

DB_PATH = os.path.join(DATA_DIR, "volcano.db")
SNAPSHOT_DIR = os.path.join(DATA_DIR, "snapshots")

def get_conn():
    """Mengembalikan koneksi SQLite."""
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=30000;")
    except Exception:
        pass
    return conn

def init_db():
    """Membuat direktori snapshot dan inisialisasi seluruh tabel database."""
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    with get_conn() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gunung TEXT NOT NULL,
                level TEXT,
                level_label TEXT,
                color TEXT,
                ringkasan TEXT,
                sumber TEXT,
                fetched_at TEXT NOT NULL,
                raw_json TEXT
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS cctv_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gunung TEXT NOT NULL,
                camera_name TEXT,
                source_url TEXT,
                local_path TEXT,
                fetched_at TEXT NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS gempa_vulkanik (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gunung TEXT NOT NULL,
                tanggal TEXT,
                jenis_gempa TEXT,
                jumlah INTEGER,
                amplitudo_max REAL,
                durasi_max REAL,
                catatan TEXT,
                fetched_at TEXT NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS gas_vulkanik (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gunung TEXT NOT NULL,
                tanggal TEXT,
                so2_flux REAL,
                co2_flux REAL,
                h2s_detected INTEGER DEFAULT 0,
                metode_pengukuran TEXT,
                catatan TEXT,
                fetched_at TEXT NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS awan_panas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gunung TEXT NOT NULL,
                tanggal TEXT,
                jenis TEXT,
                jarak_luncur_m REAL,
                arah TEXT,
                durasi_detik REAL,
                catatan TEXT,
                fetched_at TEXT NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS kubah_lava (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gunung TEXT NOT NULL,
                tanggal TEXT,
                volume_m3 REAL,
                perubahan_volume_m3 REAL,
                tinggi_m REAL,
                lokasi_kubah TEXT,
                status_morfologi TEXT,
                catatan TEXT,
                fetched_at TEXT NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS peringatan (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gunung TEXT NOT NULL,
                tipe TEXT,
                level_sebelum TEXT,
                level_sesudah TEXT,
                pesan TEXT,
                terkirim_at TEXT NOT NULL,
                channel TEXT,
                status_kirim TEXT,
                event_hash TEXT
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS gempa_realtime (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gempa_id TEXT UNIQUE,
                magnitudo REAL,
                kedalaman_km REAL,
                tanggal TEXT,
                jam TEXT,
                lat REAL,
                lon REAL,
                lokasi TEXT,
                dirasakan TEXT,
                potensi TEXT,
                sumber TEXT DEFAULT 'BMKG',
                fetched_at TEXT NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS panduan_checklist (
                item_key TEXT PRIMARY KEY,
                checked INTEGER DEFAULT 0,
                updated_at TEXT NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS telegram_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                attempts INTEGER DEFAULT 0
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS cuaca_gunung (
                gunung TEXT PRIMARY KEY,
                suhu_c REAL,
                hujan_mm REAL,
                kecepatan_angin_kmh REAL,
                kelembapan_pct REAL,
                kondisi TEXT,
                updated_at TEXT NOT NULL
            )"""
        )
        
        # Migrasi aman untuk menambahkan kolom yang mungkin belum ada
        try:
            conn.execute("ALTER TABLE kubah_lava ADD COLUMN tinggi_m REAL")
        except sqlite3.OperationalError:
            pass
            
        try:
            conn.execute("ALTER TABLE peringatan ADD COLUMN event_hash TEXT")
        except sqlite3.OperationalError:
            pass

        try:
            conn.execute("ALTER TABLE gempa_realtime ADD COLUMN sumber TEXT DEFAULT 'BMKG'")
        except sqlite3.OperationalError:
            pass

        conn.commit()
