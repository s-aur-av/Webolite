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
from datetime import datetime, timedelta
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


def create_session(admin_id):
    token = secrets.token_hex(32)
    now = now_iso()
    # 7 day expiry
    from datetime import timedelta as _td
    exp = (datetime.utcnow() + _td(days=7)).isoformat() + "Z"
    conn = get_db()
    conn.execute("INSERT INTO sessions (token, admin_id, created_at, expires_at) VALUES (?,?,?,?)",
                 (token, admin_id, now, exp))
    conn.commit()
    conn.close()
    return token

def get_session_admin(token):
    if not token:
        return None
    conn = get_db()
    try:
        conn.execute("""CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY, admin_id INTEGER NOT NULL,
            created_at TEXT NOT NULL, expires_at TEXT NOT NULL)""")
        conn.commit()
    except Exception:
        pass
    row = conn.execute(
        "SELECT admin_id, expires_at FROM sessions WHERE token=?", (token,)
    ).fetchone()
    if not row:
        conn.close()
        return None
    # Check expiry
    if row["expires_at"] < now_iso():
        conn.execute("DELETE FROM sessions WHERE token=?", (token,))
        conn.commit()
        conn.close()
        return None
    admin_id = row["admin_id"]
    conn.close()
    return admin_id

def destroy_session(token):
    if not token:
        return
    conn = get_db()
    try:
        conn.execute("DELETE FROM sessions WHERE token=?", (token,))
        conn.commit()
    except Exception:
        pass
    conn.close()


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
    CREATE TABLE IF NOT EXISTS content (
        key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT
    );
    CREATE TABLE IF NOT EXISTS visits (
        id TEXT PRIMARY KEY,
        path TEXT,
        referrer TEXT,
        user_agent TEXT,
        ip TEXT,
        session_id TEXT,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        admin_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS active_sessions (
        session_id TEXT PRIMARY KEY,
        path TEXT,
        ip TEXT,
        user_agent TEXT,
        last_seen TEXT NOT NULL,
        first_seen TEXT NOT NULL
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
        admin_id = get_session_admin(token)
        if not admin_id:
            self._error(401, "Unauthorized. Please log in.")
            return None
        return admin_id

    def _sanitize(self, val, max_len=2000):
        if not isinstance(val, str):
            return ""
        return re.sub(r"[<>]", "", val.strip())[:max_len]





    def _chat_reply(self, message):
        """Full local knowledge base for Webolite site — no external API."""
        reply = self._chat_reply_local(message)
        return reply, {"provider": "local", "model": None, "error": None}

    def _chat_reply_local(self, message):
        """Answer anything related to the Webolite website content."""
        import re
        m = (message or "").lower().strip()
        m = re.sub(r"[^\w\s$+\-./?]", " ", m)
        m = re.sub(r"\s+", " ", m).strip()

        def has(*words):
            return any(w in m for w in words)

        def any_word(*words):
            return any(re.search(r"\b" + re.escape(w) + r"\b", m) for w in words)

        # --- Greetings ---
        if re.match(r"^(hi|hello|hey|hola|namaste|yo|sup)\b", m) or m in ("hi", "hello", "hey"):
            return (
                "Hi! Welcome to Webolite — We Build. You Grow. "
                "I'm the site assistant. Ask about services, pricing (Starter / Professional / Enterprise), "
                "process, timeline, tech, SEO, portfolio, location (Rangia, Assam), or how to contact us."
            )

        if has("thank", "thanks", "thx", "appreciate"):
            return "You're welcome! When you're ready, use Get Started or the Contact form — we reply within 24 hours."

        if has("bye", "goodbye", "see you"):
            return "Goodbye! Visit the Contact section anytime. We Build. You Grow."

        # --- Brand / about ---
        if has("who are you", "your name", "are you a bot", "are you ai", "assistant", "chatbot"):
            return (
                "I'm the Webolite website assistant. I explain our services, packages, process, and how to work with us. "
                "For a custom quote, a human on our team follows up after you submit the contact form."
            )

        if has("about webolite", "what is webolite", "who is webolite", "about the company", "about your company", "about agency"):
            return (
                "Webolite is a premium web development agency. Tagline: We Build. You Grow. "
                "We help startups, businesses, institutions, and brands with modern websites, web apps, UI/UX, SEO, branding, "
                "and AI-powered solutions — designed for credibility, conversions, and growth."
            )

        if has("tagline", "slogan", "motto"):
            return 'Our tagline is "We Build. You Grow." — we craft the digital product; you scale the business.'

        # --- Location ---
        if has("location", "where are you", "address", "office", "based", "rangia", "assam", "india", "map", "city"):
            return (
                "We're based in Rangia, Assam, India. There's an embedded map in the Contact section. "
                "We work with local and remote clients worldwide."
            )

        # --- Contact ---
        if has("email", "mail", "hello@"):
            return "Email us at hello@webolite.com. You can also use the Contact form on this site — we respond within 24 hours."

        if has("phone", "call", "mobile", "number", "tel"):
            return "Phone: +1 (555) 012-3456. For a quicker chat, use WhatsApp from the Contact section or the form on this page."

        if has("whatsapp", "wa.me"):
            return "Open the Contact section and use Chat on WhatsApp, or go via the WhatsApp button linked there."

        if has("contact", "reach you", "get in touch", "talk to", "speak to"):
            return (
                "Use the Contact form (name, email, company, budget, message) — we reply within 24 hours. "
                "Or email hello@webolite.com / call +1 (555) 012-3456. Location: Rangia, Assam, India."
            )

        # --- Pricing packages ---
        if has("starter"):
            return (
                "Starter — $2,499 one-time. Ideal for startups and personal brands. "
                "Includes: custom 5-page website, mobile-responsive design, basic SEO, contact form & analytics, "
                "2 weeks support. Open the Starter page or Pricing section → Get Started."
            )

        if has("professional", "most popular"):
            return (
                "Professional — $5,999 one-time (Most Popular). For growing businesses. "
                "Includes: custom 10+ page website, advanced UI/UX, full SEO & performance, CMS integration, "
                "e-commerce ready, 1 month priority support. See Pricing or the Professional page."
            )

        if has("enterprise"):
            return (
                "Enterprise — custom pricing. For complex products and high-growth companies. "
                "Includes: custom web applications, AI integrations, dedicated team, ongoing growth partnership, "
                "SLA & priority support. Request a quote via Contact or the Enterprise page."
            )

        if has("price", "pricing", "cost", "budget", "how much", "package", "plan", "fee", "rate", "quote"):
            return (
                "Three packages:\n"
                "• Starter — $2,499 (5-page site, basic SEO, 2 weeks support)\n"
                "• Professional — $5,999 (10+ pages, full SEO, CMS, e-commerce ready, 1 month support)\n"
                "• Enterprise — custom (apps, AI, dedicated team, SLA)\n"
                "All include dedicated support and quality guarantees. Tell us your budget in the Contact form for a fit recommendation."
            )

        # --- Services ---
        if has("seo", "search engine", "google rank", "ranking"):
            return (
                "Yes — we do SEO. Basic SEO is in Starter; Professional includes full SEO & performance "
                "(technical structure, speed, on-page foundations). Stronger programs available in custom/Enterprise work."
            )

        if has("ecommerce", "e-commerce", "online store", "shop", "cart", "checkout"):
            return (
                "Yes. Professional is e-commerce ready; Enterprise covers larger catalogs and custom flows "
                "(payments, inventory, integrations). Share product volume and payment needs in Contact for a quote."
            )

        if has("ui", "ux", "design", "interface", "figma", "branding", "brand"):
            return (
                "We offer UI/UX design and branding: research-backed interfaces, visual systems, and conversion-focused layouts. "
                "Professional emphasizes advanced UI/UX; branding can be scoped into any package or as a standalone engagement."
            )

        if has("web app", "application", "saas", "platform", "dashboard"):
            return (
                "We build web applications and digital products — dashboards, SaaS-style platforms, custom tools. "
                "That's typically Enterprise / custom scope with a dedicated team."
            )

        if has("ai", "artificial intelligence", "machine learning", "automation", "chatbot for my"):
            return (
                "We deliver AI-powered solutions: on-site assistants, smart forms, automation, and product features. "
                "Enterprise highlights AI integrations. Describe your use case in the Contact form."
            )

        if has("service", "offer", "what do you do", "what can you", "help with", "capability", "work do you"):
            return (
                "Services: modern websites, web applications, UI/UX design, SEO, branding, e-commerce, "
                "and AI-powered solutions. Built for credibility, conversions, and growth across startups, SMBs, "
                "education, healthcare, hospitality, agencies, personal brands, and online stores."
            )

        # --- Process & timeline ---
        if has("process", "how do you work", "workflow", "steps", "methodology", "phases"):
            return (
                "Process: 1) Discovery & strategy 2) Design 3) Development 4) Review & launch 5) Growth support. "
                "You get clear milestones and stay involved. Start via Get Started or Contact."
            )

        if has("time", "timeline", "how long", "duration", "deadline", "how soon", "weeks", "months", "delivery"):
            return (
                "Typical timelines: Starter about 2–4 weeks; Professional about 4–8 weeks; "
                "Enterprise depends on scope. Support windows: Starter 2 weeks, Professional 1 month priority, "
                "Enterprise ongoing/SLA. We'll confirm dates after discovery."
            )

        if has("support", "maintain", "maintenance", "after launch"):
            return (
                "Starter includes 2 weeks support; Professional 1 month priority support; "
                "Enterprise includes ongoing partnership and SLA options. Longer maintenance can be arranged after launch."
            )

        # --- Tech ---
        if has("tech", "technology", "stack", "framework", "react", "next", "node", "python", "wordpress", "tools"):
            return (
                "We use modern stacks suited to the project — performance-first frontends, solid backends, SEO-friendly structure, "
                "and clean CMS/e-commerce integrations when needed. Exact tools are chosen in discovery so they fit your goals."
            )

        # --- Portfolio / clients / audience ---
        if has("portfolio", "projects", "case study", "examples", "work samples", "selected projects"):
            return (
                "See Selected Projects on this homepage — work chosen to show design quality, performance, and results. "
                "Want something similar? Tell us your industry in Contact."
            )

        if has("client", "testimonial", "review", "feedback"):
            return (
                "Client testimonials are on the homepage (What Our Clients Say). "
                "You can also submit a review from the site; approved reviews appear publicly."
            )

        if has("who do you work", "industries", "audience", "startup", "restaurant", "hotel", "healthcare", "education"):
            return (
                "We work with startups, small & medium businesses, education, healthcare, restaurants, hotels, "
                "agencies, personal brands, freelancers, and e-commerce. If you have a growth goal, we can usually help."
            )

        # --- FAQ-ish ---
        if has("payment", "pay", "invoice", "refund"):
            return (
                "Pricing is package-based (Starter / Professional one-time listed prices; Enterprise custom). "
                "Payment schedule is confirmed in the proposal after discovery. Ask about milestones when you contact us."
            )

        if has("own domain", "hosting", "domain"):
            return (
                "We can work with your domain and preferred hosting, or advise on setup. "
                "Details are fixed during discovery so launch is smooth."
            )

        if has("revise", "revision", "changes", "unlimited"):
            return (
                "Each package includes structured review rounds. Extra revisions beyond scope can be added. "
                "We'll spell this out in your proposal so expectations stay clear."
            )

        if has("admin", "login", "password", "cms login"):
            return (
                "Site admin for Webolite owners is at /admin.html with your own credentials. "
                "We never share passwords in chat. Client CMS logins are delivered at project handoff."
            )

        if has("newsletter", "subscribe"):
            return "Use the email box in the footer to subscribe for updates from Webolite."

        if has("get started", "hire you", "start a project", "begin", "kickoff", "onboard"):
            return (
                "Click Get Started (or open Starter / Professional / Enterprise pages), or fill the Contact form "
                "with your goals and budget. We'll reply within 24 hours with next steps."
            )

        # --- Light / dark / site UI ---
        if has("dark mode", "light mode", "theme"):
            return "Use the sun/moon toggle in the header to switch light and dark mode."

        # --- Default: guided help ---
        return (
            "I can help with anything on this site: services, Starter ($2,499) / Professional ($5,999) / Enterprise (custom), "
            "process, timelines, SEO, e-commerce, AI, portfolio, location (Rangia, Assam), or contact (hello@webolite.com). "
            "Try asking: “What's in Professional?” or “How long does a Starter site take?”"
        )


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
        # Normalize root
        if path == "/" or path == "":
            path = "/index.html"
        # Security: resolve and stay inside ROOT
        file_path = (ROOT / path.lstrip("/")).resolve()
        if not str(file_path).startswith(str(ROOT)):
            return self._error(403, "Forbidden")
        # Missing file: only fall back to index for unknown SPA routes,
        # never for explicit files like admin.html, style.css, etc.
        if not file_path.is_file():
            # If they asked for a real file extension, 404 with clear message
            ext = file_path.suffix.lower()
            if ext in (".html", ".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg",
                       ".mp4", ".webm", ".ico", ".json", ".xml", ".txt", ".woff", ".woff2"):
                msg = f"File not found: {path}. Put admin.html in the same folder as server.py"
                print(f"  [404] {path}")
                return self._error(404, msg)
            # Bare path fallback (SPA-style)
            file_path = ROOT / "index.html"
            if not file_path.is_file():
                return self._error(404, "index.html not found")
        ctype = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        if file_path.suffix.lower() == ".js":
            ctype = "application/javascript; charset=utf-8"
        elif file_path.suffix.lower() == ".css":
            ctype = "text/css; charset=utf-8"
        elif file_path.suffix.lower() in (".html", ".htm"):
            ctype = "text/html; charset=utf-8"
        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
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

        
        if path == "/api/content":
            rows = conn.execute("SELECT key, value FROM content").fetchall()
            data = {}
            for r in rows:
                try:
                    data[r["key"]] = json.loads(r["value"])
                except Exception:
                    data[r["key"]] = r["value"]
            conn.close()
            return self._json(200, {"success": True, "data": data})

        if path.startswith("/api/content/"):
            key = path.rstrip("/").split("/")[-1]
            row = conn.execute("SELECT value FROM content WHERE key=?", (key,)).fetchone()
            conn.close()
            if not row:
                return self._error(404, "Content not found")
            try:
                val = json.loads(row["value"])
            except Exception:
                val = row["value"]
            return self._json(200, {"success": True, "key": key, "data": val})

        if path == "/api/settings":
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
            settings = {r["key"]: r["value"] for r in rows}
            if "stats" in settings:
                try: settings["stats"] = json.loads(settings["stats"])
                except: pass
            conn.close()
            return self._json(200, {"success": True, "data": settings})

        
        if path == "/api/admin/analytics" or path == "/api/analytics":
            if not self._require_auth():
                conn.close(); return
            # Ensure tables exist
            try:
                conn.execute("""CREATE TABLE IF NOT EXISTS visits (
                    id TEXT PRIMARY KEY, path TEXT, referrer TEXT, user_agent TEXT,
                    ip TEXT, session_id TEXT, created_at TEXT NOT NULL)""")
                conn.execute("""CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        admin_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS active_sessions (
                    session_id TEXT PRIMARY KEY, path TEXT, ip TEXT, user_agent TEXT,
                    last_seen TEXT NOT NULL, first_seen TEXT NOT NULL)""")
                conn.commit()
            except Exception:
                pass
            cutoff = (datetime.utcnow() - timedelta(minutes=2)).isoformat() + "Z"
            active = conn.execute(
                "SELECT * FROM active_sessions WHERE last_seen > ? ORDER BY last_seen DESC",
                (cutoff,)
            ).fetchall()
            today = conn.execute(
                "SELECT COUNT(*) AS n FROM visits WHERE date(created_at) = date('now')"
            ).fetchone()["n"]
            total = conn.execute("SELECT COUNT(*) AS n FROM visits").fetchone()["n"]
            # Top pages today
            top_pages = conn.execute(
                """SELECT path, COUNT(*) AS views FROM visits
                   WHERE date(created_at) = date('now')
                   GROUP BY path ORDER BY views DESC LIMIT 10"""
            ).fetchall()
            # Recent visits
            recent = conn.execute(
                "SELECT * FROM visits ORDER BY created_at DESC LIMIT 20"
            ).fetchall()
            # Hourly today
            hourly = conn.execute(
                """SELECT strftime('%H', created_at) AS hour, COUNT(*) AS views
                   FROM visits WHERE date(created_at) = date('now')
                   GROUP BY hour ORDER BY hour"""
            ).fetchall()
            conn.close()
            return self._json(200, {
                "success": True,
                "data": {
                    "activeNow": len(active),
                    "activeSessions": [
                        {"sessionId": r["session_id"], "path": r["path"], "ip": r["ip"],
                         "userAgent": r["user_agent"], "lastSeen": r["last_seen"], "firstSeen": r["first_seen"]}
                        for r in active
                    ],
                    "todayViews": today,
                    "totalViews": total,
                    "topPages": [{"path": r["path"], "views": r["views"]} for r in top_pages],
                    "recent": [
                        {"id": r["id"], "path": r["path"], "referrer": r["referrer"],
                         "ip": r["ip"], "userAgent": r["user_agent"], "createdAt": r["created_at"]}
                        for r in recent
                    ],
                    "hourly": [{"hour": r["hour"], "views": r["views"]} for r in hourly],
                }
            })

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

        

        if path == "/api/chat":
            msg = (body.get("message") or body.get("q") or "").strip()
            if not msg:
                return self._json(400, {"success": False, "error": "Message required"})
            result = self._chat_reply(msg)
            if isinstance(result, tuple):
                reply, meta = result
            else:
                reply, meta = result, {"provider": "local"}
            return self._json(200, {
                "success": True,
                "reply": reply,
                "provider": meta.get("provider", "local"),
                "model": meta.get("model"),
                "llm_error": meta.get("error"),
            })

        
        if path == "/api/track":
            path_url = self._sanitize(body.get("path", "/"), 300)
            referrer = self._sanitize(body.get("referrer", ""), 400)
            session_id = self._sanitize(body.get("sessionId", ""), 64) or uid()
            ua = self._sanitize(self.headers.get("User-Agent", ""), 300)
            ip = self.headers.get("X-Forwarded-For", self.client_address[0] if self.client_address else "")
            ip = self._sanitize(str(ip).split(",")[0].strip(), 60)
            now = now_iso()
            vid = uid()
            # Log visit only on pageview type (not heartbeat)
            event = (body.get("type") or "pageview").lower()
            if event == "pageview":
                conn.execute(
                    "INSERT INTO visits (id,path,referrer,user_agent,ip,session_id,created_at) VALUES (?,?,?,?,?,?,?)",
                    (vid, path_url, referrer, ua, ip, session_id, now)
                )
            # Upsert active session
            conn.execute(
                """INSERT INTO active_sessions (session_id, path, ip, user_agent, last_seen, first_seen)
                   VALUES (?,?,?,?,?,?)
                   ON CONFLICT(session_id) DO UPDATE SET path=excluded.path, last_seen=excluded.last_seen""",
                (session_id, path_url, ip, ua, now, now)
            )
            # Cleanup old sessions (>1 hour)
            try:
                conn.execute("DELETE FROM active_sessions WHERE last_seen < datetime('now', '-1 hour')")
            except Exception:
                pass
            conn.commit()
            conn.close()
            return self._json(200, {"success": True, "sessionId": session_id})

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
            token = create_session(row["id"])
            print(f"  [LOGIN] {email}")
            return self._json(200, {"success": True, "token": token, "admin": {"id": row["id"], "email": row["email"], "name": row["name"]}})

        if path == "/api/admin/logout":
            t = self._token()
            destroy_session(t)
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

        
        if path.startswith("/api/admin/content/"):
            if not self._require_auth():
                conn.close(); return
            key = path.rstrip("/").split("/")[-1]
            # body can be the content object directly or { data: ... }
            payload = body.get("data", body)
            conn.execute(
                "INSERT OR REPLACE INTO content (key, value, updated_at) VALUES (?,?,?)",
                (key, json.dumps(payload), now_iso())
            )
            conn.commit()
            conn.close()
            return self._json(200, {"success": True, "key": key, "message": "Content saved"})

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
