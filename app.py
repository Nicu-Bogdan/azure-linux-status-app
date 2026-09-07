from flask import Flask, jsonify
import psutil
import psycopg2
import os
from datetime import datetime
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST


app = Flask(__name__)

DB_HOST = os.environ.get("DB_HOST", "db")
DB_NAME = os.environ.get("DB_NAME", "statusdb")
DB_USER = os.environ.get("DB_USER", "statususer")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "changeme")

snapshot_counter = Counter('app_snapshots_total', 'Numarul total de snapshot-uri create')
cpu_gauge = Gauge('app_last_cpu_percent', 'Ultimul CPU procentual masurat')
memory_gauge = Gauge('app_last_memory_percent', 'Ultima memorie procentuala masurata')


def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id SERIAL PRIMARY KEY,
            cpu_percent FLOAT,
            memory_percent FLOAT,
            uptime_seconds FLOAT,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

@app.route("/snapshot", methods=["POST"])
def create_snapshot():
    cpu = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory().percent
    uptime = datetime.now().timestamp() - psutil.boot_time()

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO snapshots (cpu_percent, memory_percent, uptime_seconds) VALUES (%s, %s, %s) RETURNING id",
        (cpu, memory, uptime)
    )
    new_id = cur.fetchone()[0]
    conn.commit()

    snapshot_counter.inc()
    cpu_gauge.set(cpu)
    memory_gauge.set(memory)
    cur.close()
    conn.close()

    return jsonify({
        "id": new_id,
        "cpu_percent": cpu,
        "memory_percent": memory,
        "uptime_seconds": uptime
    }), 201

@app.route("/history", methods=["GET"])
def get_history():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, cpu_percent, memory_percent, uptime_seconds, created_at FROM snapshots ORDER BY created_at DESC LIMIT 50")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    history = [
        {
            "id": row[0],
            "cpu_percent": row[1],
            "memory_percent": row[2],
            "uptime_seconds": row[3],
            "created_at": row[4].isoformat()
        }
        for row in rows
    ]
    return jsonify(history)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "version": "1.1"})

@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
