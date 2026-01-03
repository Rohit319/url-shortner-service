
from flask import Flask, request, jsonify, redirect
import sqlite3
import string
import random
import time

app = Flask(__name__)

# -----------------------------
# DATABASE (SQLite)
# -----------------------------
def init_db():
    conn = sqlite3.connect("urls.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS urls (
            short_code TEXT PRIMARY KEY,
            long_url TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# -----------------------------
# RATE LIMITING
# -----------------------------
RATE_LIMIT = 5          # max requests
TIME_WINDOW = 60        # seconds
user_requests = {}      # ip -> [timestamps]

def is_rate_limited(ip):
    now = time.time()
    if ip not in user_requests:
        user_requests[ip] = []

    # keep only last 60 seconds requests
    user_requests[ip] = [t for t in user_requests[ip] if now - t < TIME_WINDOW]

    if len(user_requests[ip]) >= RATE_LIMIT:
        return True

    user_requests[ip].append(now)
    return False

# -----------------------------
# SHORT CODE GENERATOR
# -----------------------------
def generate_short_code(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

# -----------------------------
# HOME (OPTIONAL)
# -----------------------------
@app.route('/')
def home():
    return "URL Shortener API is running"

# -----------------------------
# REST API: SHORTEN URL
# -----------------------------
@app.route('/api/shorten', methods=['POST'])
def shorten_url():
    ip = request.remote_addr

    if is_rate_limited(ip):
        return jsonify({"error": "Rate limit exceeded"}), 429

    data = request.get_json()
    if not data or "long_url" not in data:
        return jsonify({"error": "long_url required"}), 400

    long_url = data["long_url"]
    short_code = generate_short_code()

    conn = sqlite3.connect("urls.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO urls (short_code, long_url) VALUES (?, ?)",
        (short_code, long_url)
    )
    conn.commit()
    conn.close()

    return jsonify({
        "short_url": f"http://127.0.0.1:5000/{short_code}"
    })

# -----------------------------
# REDIRECT SHORT URL
# -----------------------------
@app.route('/<short_code>')
def redirect_url(short_code):
    conn = sqlite3.connect("urls.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT long_url FROM urls WHERE short_code = ?",
        (short_code,)
    )
    result = cursor.fetchone()
    conn.close()

    if result:
        return redirect(result[0])
    return "URL not found", 404

# -----------------------------
# RUN SERVER
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
