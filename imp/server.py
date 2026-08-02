#!/usr/bin/env python3
"""Webolite Fullstack Server - Python 3 + SQLite"""

import http.server
import json
import os
import re
import sqlite3
import hashlib
import secrets
import mimetypes
from datetime import datetime
from urllib.parse import urlparse, unquote
from pathlib import Path

PORT = int(os.environ.get("PORT", 3000))
HOST = os.environ.get("HOST", "0.0.0.0")
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "webolite.db"
DATA_DIR.mkdir(exist_ok=True)
SESSIONS = {}

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return salt, h.hex()

def verify_password(password, salt, password_hash):
    _, h = hash_password(password, salt)
    return h == password_hash

def uid():
    return secrets.token_hex(12)

def now_iso():
    return datetime.utcnow().isoformat() + "Z"

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        name TEXT DEFAULT 'Admin',
        salt TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS contacts (
        id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL,
        company TEXT, budget TEXT, message TEXT NOT NULL, created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS newsletter (
        id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS testimonials (
        id TEXT PRIMARY KEY, name TEXT NOT NULL, position TEXT, company TEXT,
        rating INTEGER DEFAULT 5, text TEXT NOT NULL, avatar TEXT,
        status TEXT DEFAULT 'pending', created_at TEXT NOT NULL, moderated_at TEXT
    );
    CREATE TABLE IF NOT EXISTS portfolio (
        id TEXT PRIMARY KEY, title TEXT NOT NULL, category TEXT DEFAULT 'web',
        cat_label TEXT DEFAULT 'Project', gradient TEXT DEFAULT 'gradient-1',
        tags TEXT DEFAULT '[]', image TEXT DEFAULT '', demo_url TEXT DEFAULT '#',
        case_url TEXT DEFAULT '#', created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY, value TEXT NOT NULL
    );
    """)
    row = c.execute("SELECT COUNT(*) AS n FROM admins").fetchone()
    if row["n"] == 0:
        salt, pw_hash = hash_password("admin123")
        c.execute("INSERT INTO admins (email,name,salt,password_hash,created_at) VALUES (?,?,?,?,?)",
                  ("admin@webolite.com", "Super Admin", salt, pw_hash, now_iso()))
        print("  [DB] Default admin: admin@webolite.com / admin123")
    defaults = {
        "heroTitle": "We Build.\\nYou Grow.",
        "heroSubtitle": "Crafting world-class websites, web applications, and digital products that elevate brands and accelerate business growth.",
        "stats": json.dumps({"projects": 150, "satisfaction": 98, "years": 12, "clients": 85}),
        "contactEmail": "hello@webolite.com",
        "contactPhone": "+1 (555) 012-3456",
    }
    for k, v in defaults.items():
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
    row = c.execute("SELECT COUNT(*) AS n FROM portfolio").fetchone()
    if row["n"] == 0:
        seeds = [
            ("p1","Aether Analytics Platform","web design","SaaS Website","gradient-1",'["Next.js","TypeScript","Tailwind"]'),
            ("p2","Lumina Fashion Store","ecommerce","E-commerce","gradient-2",'["Shopify","React","Stripe"]'),
            ("p3","Pulse Project Management","app","Web Application","gradient-3",'["React","Node.js","PostgreSQL"]'),
            ("p4","Vertex Health Portal","design web","Healthcare","gradient-4",'["Figma","Framer","Webflow"]'),
            ("p5","Orbit AI Assistant","app","AI Product","gradient-5",'["Vue","Python","OpenAI"]'),
            ("p6","Nexus Enterprise Store","ecommerce design","B2B Commerce","gradient-6",'["Next.js","Shopify Plus","GraphQL"]'),
        ]
        for s in seeds:
            c.execute("INSERT INTO portfolio (id,title,category,cat_label,gradient,tags,image,demo_url,case_url,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                      (*s, "", "#", "#", now_iso()))
    row = c.execute("SELECT COUNT(*) AS n FROM testimonials").fetchone()
    if row["n"] == 0:
        seeds = [
            ("t1","Sarah Kline","CEO","Aether Analytics",5,"Webolite transformed our outdated site into a conversion machine. Traffic is up 340%.","SK"),
            ("t2","Marcus Rivera","Founder","Pulse Labs",5,"Working with Webolite felt like having an elite product team in-house.","MR"),
            ("t3","Elena Vargas","CMO","Lumina Fashion",5,"They rebuilt our entire digital presence. Revenue grew 2.8x within six months.","EL"),
            ("t4","James Thornton","Director","Vertex Health",5,"From strategy to launch, the process was seamless. Exceeded every expectation.","JT"),
        ]
        for s in seeds:
            c.execute("INSERT INTO testimonials (id,name,position,company,rating,text,avatar,status,created_at) VALUES (?,?,?,?,?,?,?,'approved',?)",
                      (*s, now_iso()))
    conn.commit()
    conn.close()

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"  [{self.command}] {args[0] if args else ''}")

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def _json(self, status, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _error(self, status, msg):
        self._json(status, {"success": False, "error": msg})

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length > 1000000:
            return None
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            return {}

    def _token(self):
        auth = self.headers.get("Authorization", "")
        return auth[7:] if auth.startswith("Bearer ") else None

    def _require_auth(self):
        token = self._token()
        if not token or token not in SESSIONS:
            self._error(401, "Unauthorized. Please log in.")
            return None
        return SESSIONS[token]

    def _sanitize(self, val, max_len=2000):
        if not isinstance(val, str):
            return ""
        return re.sub(r"[<>]", "", val.strip())[:max_len]

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path.startswith("/api/"):
            return self._api_get(path)
        if path == "/":
            path = "/index.html"
        file_path = (ROOT / path.lstrip("/")).resolve()
        if not str(file_path).startswith(str(ROOT)) or not file_path.is_file():
            file_path = ROOT / "index.html"
            if not file_path.is_file():
                return self._error(404, "Not found")
        ctype = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self._cors()
        self.end_headers()
        self.wfile.write(data)

    def _api_get(self, path):
        conn = get_db()
        if path == "/api/health":
            stats = {
                "contacts": conn.execute("SELECT COUNT(*) AS n FROM contacts").fetchone()["n"],
                "subscribers": conn.execute("SELECT COUNT(*) AS n FROM newsletter").fetchone()["n"],
                "testimonials": conn.execute("SELECT COUNT(*) AS n FROM testimonials").fetchone()["n"],
                "portfolio": conn.execute("SELECT COUNT(*) AS n FROM portfolio").fetchone()["n"],
                "admins": conn.execute("SELECT COUNT(*) AS n FROM admins").fetchone()["n"],
            }
            conn.close()
            return self._json(200, {"status": "ok", "service": "Webolite API", "version": "2.0.0", "database": "SQLite", "stats": stats})

        if path == "/api/testimonials":
            rows = conn.execute("SELECT * FROM testimonials WHERE status='approved' ORDER BY created_at DESC").fetchall()
            data = [{"id": r["id"], "name": r["name"], "position": r["position"], "company": r["company"],
                     "rating": r["rating"], "text": r["text"], "avatar": r["avatar"], "status": r["status"],
                     "createdAt": r["created_at"]} for r in rows]
            conn.close()
            return self._json(200, {"success": True, "count": len(data), "data": data})

        if path == "/api/portfolio":
            rows = conn.execute("SELECT * FROM portfolio ORDER BY created_at DESC").fetchall()
            data = [{"id": r["id"], "title": r["title"], "category": r["category"], "catLabel": r["cat_label"],
                     "gradient": r["gradient"], "tags": json.loads(r["tags"] or "[]"), "image": r["image"],
                     "demoUrl": r["demo_url"], "caseUrl": r["case_url"], "createdAt": r["created_at"]} for r in rows]
            conn.close()
            return self._json(200, {"success": True, "count": len(data), "data": data})

        if path == "/api/settings":
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
            settings = {r["key"]: r["value"] for r in rows}
            if "stats" in settings:
                try: settings["stats"] = json.loads(settings["stats"])
                except: pass
            conn.close()
            return self._json(200, {"success": True, "data": settings})

        if path == "/api/admin/contacts":
            if not self._require_auth():
                conn.close(); return
            rows = conn.execute("SELECT * FROM contacts ORDER BY created_at DESC").fetchall()
            data = [{"id": r["id"], "name": r["name"], "email": r["email"], "company": r["company"],
                     "budget": r["budget"], "message": r["message"], "createdAt": r["created_at"]} for r in rows]
            conn.close()
            return self._json(200, {"success": True, "count": len(data), "data": data})

        if path == "/api/admin/testimonials":
            if not self._require_auth():
                conn.close(); return
            rows = conn.execute("SELECT * FROM testimonials ORDER BY created_at DESC").fetchall()
            data = [{"id": r["id"], "name": r["name"], "position": r["position"], "company": r["company"],
                     "rating": r["rating"], "text": r["text"], "avatar": r["avatar"], "status": r["status"],
                     "createdAt": r["created_at"]} for r in rows]
            conn.close()
            return self._json(200, {"success": True, "count": len(data), "data": data})

        if path == "/api/admin/newsletter":
            if not self._require_auth():
                conn.close(); return
            rows = conn.execute("SELECT * FROM newsletter ORDER BY created_at DESC").fetchall()
            data = [{"id": r["id"], "email": r["email"], "createdAt": r["created_at"]} for r in rows]
            conn.close()
            return self._json(200, {"success": True, "count": len(data), "data": data})

        if path == "/api/admin/users":
            if not self._require_auth():
                conn.close(); return
            rows = conn.execute("SELECT id, email, name, created_at FROM admins ORDER BY created_at DESC").fetchall()
            data = [{"id": r["id"], "email": r["email"], "name": r["name"], "createdAt": r["created_at"]} for r in rows]
            conn.close()
            return self._json(200, {"success": True, "count": len(data), "data": data})

        conn.close()
        self._error(404, "Not found")

    def do_POST(self):
        path = unquote(urlparse(self.path).path)
        body = self._read_body()
        if body is None:
            return self._error(413, "Too large")
        conn = get_db()

        if path == "/api/admin/login":
            email = self._sanitize(body.get("email", ""), 150).lower()
            password = body.get("password", "")
            if not email or not password:
                conn.close()
                return self._error(400, "Email and password required")
            row = conn.execute("SELECT * FROM admins WHERE email=?", (email,)).fetchone()
            conn.close()
            if not row or not verify_password(password, row["salt"], row["password_hash"]):
                return self._error(401, "Invalid email or password")
            token = secrets.token_hex(32)
            SESSIONS[token] = row["id"]
            print(f"  [LOGIN] {email}")
            return self._json(200, {"success": True, "token": token, "admin": {"id": row["id"], "email": row["email"], "name": row["name"]}})

        if path == "/api/admin/logout":
            t = self._token()
            if t: SESSIONS.pop(t, None)
            conn.close()
            return self._json(200, {"success": True})

        if path == "/api/contact":
            name = self._sanitize(body.get("name",""), 100)
            email = self._sanitize(body.get("email",""), 150).lower()
            message = self._sanitize(body.get("message",""), 3000)
            if not name or not email or not message:
                conn.close(); return self._error(400, "Name, email, message required")
            cid = uid()
            conn.execute("INSERT INTO contacts (id,name,email,company,budget,message,created_at) VALUES (?,?,?,?,?,?,?)",
                (cid, name, email, self._sanitize(body.get("company",""),120), self._sanitize(body.get("budget",""),50), message, now_iso()))
            conn.commit(); conn.close()
            return self._json(201, {"success": True, "message": "Thank you!", "id": cid})

        if path == "/api/newsletter":
            email = self._sanitize(body.get("email",""), 150).lower()
            if not email:
                conn.close(); return self._error(400, "Email required")
            if conn.execute("SELECT id FROM newsletter WHERE email=?", (email,)).fetchone():
                conn.close(); return self._json(200, {"success": True, "message": "Already subscribed"})
            nid = uid()
            conn.execute("INSERT INTO newsletter (id,email,created_at) VALUES (?,?,?)", (nid, email, now_iso()))
            conn.commit(); conn.close()
            return self._json(201, {"success": True, "message": "Subscribed!"})

        if path == "/api/testimonials":
            name = self._sanitize(body.get("name",""), 80)
            text = self._sanitize(body.get("text",""), 800)
            if not name or len(text) < 10:
                conn.close(); return self._error(400, "Name and review (10+ chars) required")
            try: rating = max(1, min(5, int(body.get("rating", 5))))
            except: rating = 5
            parts = name.split()
            avatar = (parts[0][0]+parts[-1][0]).upper() if len(parts)>=2 else name[:2].upper()
            tid = uid()
            conn.execute("INSERT INTO testimonials (id,name,position,company,rating,text,avatar,status,created_at) VALUES (?,?,?,?,?,?,?,'pending',?)",
                (tid, name, self._sanitize(body.get("position","Client"),80), self._sanitize(body.get("company",""),100), rating, text, avatar, now_iso()))
            conn.commit(); conn.close()
            return self._json(201, {"success": True, "message": "Pending moderation", "id": tid})

        if path == "/api/admin/users":
            if not self._require_auth():
                conn.close(); return
            email = self._sanitize(body.get("email",""), 150).lower()
            password = body.get("password", "")
            name = self._sanitize(body.get("name","Admin"), 80)
            if not email or not password:
                conn.close(); return self._error(400, "Email and password required")
            if len(password) < 6:
                conn.close(); return self._error(400, "Password min 6 characters")
            if conn.execute("SELECT id FROM admins WHERE email=?", (email,)).fetchone():
                conn.close(); return self._error(400, "Email already exists")
            salt, pw_hash = hash_password(password)
            c = conn.execute("INSERT INTO admins (email,name,salt,password_hash,created_at) VALUES (?,?,?,?,?)",
                             (email, name, salt, pw_hash, now_iso()))
            conn.commit()
            new_id = c.lastrowid
            conn.close()
            return self._json(201, {"success": True, "data": {"id": new_id, "email": email, "name": name}})

        if path == "/api/admin/portfolio":
            if not self._require_auth():
                conn.close(); return
            title = self._sanitize(body.get("title",""), 120)
            if not title:
                conn.close(); return self._error(400, "Title required")
            pid = uid()
            tags = body.get("tags", []) if isinstance(body.get("tags"), list) else []
            conn.execute("INSERT INTO portfolio (id,title,category,cat_label,gradient,tags,image,demo_url,case_url,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (pid, title, self._sanitize(body.get("category","web"),60), self._sanitize(body.get("catLabel","Project"),60),
                 self._sanitize(body.get("gradient","gradient-1"),20), json.dumps(tags[:6]),
                 self._sanitize(body.get("image",""),500), self._sanitize(body.get("demoUrl","#"),300),
                 self._sanitize(body.get("caseUrl","#"),300), now_iso()))
            conn.commit(); conn.close()
            return self._json(201, {"success": True, "data": {"id": pid, "title": title}})

        if path.startswith("/api/admin/testimonials/"):
            if not self._require_auth():
                conn.close(); return
            tid = path.rstrip("/").split("/")[-1]
            status = (body.get("status") or "").lower()
            if status not in ("approved","rejected","pending"):
                conn.close(); return self._error(400, "Invalid status")
            conn.execute("UPDATE testimonials SET status=?, moderated_at=? WHERE id=?", (status, now_iso(), tid))
            conn.commit(); conn.close()
            return self._json(200, {"success": True, "message": f"Testimonial {status}"})

        conn.close()
        self._error(404, "Not found")

    def do_PUT(self):
        path = unquote(urlparse(self.path).path)
        body = self._read_body() or {}
        conn = get_db()

        if path == "/api/admin/settings":
            if not self._require_auth():
                conn.close(); return
            for k in ("heroTitle","heroSubtitle","contactEmail","contactPhone"):
                if k in body and body[k] is not None:
                    conn.execute("INSERT OR REPLACE INTO settings (key,value) VALUES (?,?)", (k, self._sanitize(str(body[k]), 500)))
            if body.get("stats"):
                conn.execute("INSERT OR REPLACE INTO settings (key,value) VALUES (?,?)", ("stats", json.dumps(body["stats"])))
            conn.commit()
            rows = conn.execute("SELECT key,value FROM settings").fetchall()
            settings = {r["key"]: r["value"] for r in rows}
            if "stats" in settings:
                try: settings["stats"] = json.loads(settings["stats"])
                except: pass
            conn.close()
            return self._json(200, {"success": True, "data": settings})

        if path.startswith("/api/admin/portfolio/"):
            if not self._require_auth():
                conn.close(); return
            pid = path.rstrip("/").split("/")[-1]
            if not conn.execute("SELECT id FROM portfolio WHERE id=?", (pid,)).fetchone():
                conn.close(); return self._error(404, "Not found")
            updates = []
            vals = []
            mapping = [("title","title",120),("category","category",60),("catLabel","cat_label",60),
                       ("gradient","gradient",20),("image","image",500),("demoUrl","demo_url",300),("caseUrl","case_url",300)]
            for bk, col, mx in mapping:
                if bk in body:
                    updates.append(f"{col}=?"); vals.append(self._sanitize(str(body[bk]), mx))
            if "tags" in body and isinstance(body["tags"], list):
                updates.append("tags=?"); vals.append(json.dumps(body["tags"][:6]))
            if updates:
                vals.append(pid)
                conn.execute(f"UPDATE portfolio SET {', '.join(updates)} WHERE id=?", vals)
                conn.commit()
            conn.close()
            return self._json(200, {"success": True})

        if path == "/api/admin/password":
            admin_id = self._require_auth()
            if not admin_id:
                conn.close(); return
            old_pw = body.get("oldPassword","")
            new_pw = body.get("newPassword","")
            if not old_pw or not new_pw or len(new_pw) < 6:
                conn.close(); return self._error(400, "Invalid password data")
            row = conn.execute("SELECT * FROM admins WHERE id=?", (admin_id,)).fetchone()
            if not row or not verify_password(old_pw, row["salt"], row["password_hash"]):
                conn.close(); return self._error(401, "Current password incorrect")
            salt, pw_hash = hash_password(new_pw)
            conn.execute("UPDATE admins SET salt=?, password_hash=? WHERE id=?", (salt, pw_hash, admin_id))
            conn.commit(); conn.close()
            return self._json(200, {"success": True, "message": "Password updated"})

        conn.close()
        self._error(404, "Not found")

    def do_DELETE(self):
        path = unquote(urlparse(self.path).path)
        if not self._require_auth():
            return
        conn = get_db()
        tables = {
            "/api/admin/contacts/": "contacts",
            "/api/admin/testimonials/": "testimonials",
            "/api/admin/newsletter/": "newsletter",
            "/api/admin/portfolio/": "portfolio",
        }
        for prefix, table in tables.items():
            if path.startswith(prefix):
                item_id = path.rstrip("/").split("/")[-1]
                conn.execute(f"DELETE FROM {table} WHERE id=?", (item_id,))
                conn.commit(); conn.close()
                return self._json(200, {"success": True, "message": "Deleted"})

        if path.startswith("/api/admin/users/"):
            uid_del = path.rstrip("/").split("/")[-1]
            if conn.execute("SELECT COUNT(*) AS n FROM admins").fetchone()["n"] <= 1:
                conn.close(); return self._error(400, "Cannot delete last admin")
            conn.execute("DELETE FROM admins WHERE id=?", (uid_del,))
            conn.commit(); conn.close()
            return self._json(200, {"success": True, "message": "Admin deleted"})

        conn.close()
        self._error(404, "Not found")

if __name__ == "__main__":
    init_db()
    server = http.server.HTTPServer((HOST, PORT), Handler)
    print()
    print("  ========================================")
    print("    Webolite Server (Python + SQLite)")
    print("  ========================================")
    print(f"  Local:    http://localhost:{PORT}")
    print(f"  Admin:    http://localhost:{PORT}/admin.html")
    print(f"  Database: {DB_PATH}")
    print()
    print("  LOGIN CREDENTIALS:")
    print("    Email:    admin@webolite.com")
    print("    Password: admin123")
    print()
    print("  Press Ctrl+C to stop")
    print()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Shutting down...")
        server.server_close()
