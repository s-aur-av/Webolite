/**
 * Webolite — Fullstack Backend
 * Pure Node.js (zero dependencies)
 * Serves static frontend + REST API
 */

const http = require('http');
const fs = require('fs');
const path = require('path');
const { URL } = require('url');
const crypto = require('crypto');

const PORT = process.env.PORT || 3000;
const HOST = process.env.HOST || '0.0.0.0';
const ROOT = __dirname;
const DATA_DIR = path.join(ROOT, 'data');
const CONTACTS_FILE = path.join(DATA_DIR, 'contacts.json');
const NEWSLETTER_FILE = path.join(DATA_DIR, 'newsletter.json');
const TESTIMONIALS_FILE = path.join(DATA_DIR, 'testimonials.json');
const PORTFOLIO_FILE = path.join(DATA_DIR, 'portfolio.json');
const SETTINGS_FILE = path.join(DATA_DIR, 'settings.json');

// Admin password — change this!
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'webolite2026';
const activeTokens = new Set();

// Ensure data directory & files exist
if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });
if (!fs.existsSync(CONTACTS_FILE)) fs.writeFileSync(CONTACTS_FILE, '[]');
if (!fs.existsSync(NEWSLETTER_FILE)) fs.writeFileSync(NEWSLETTER_FILE, '[]');
if (!fs.existsSync(TESTIMONIALS_FILE)) fs.writeFileSync(TESTIMONIALS_FILE, '[]');
if (!fs.existsSync(PORTFOLIO_FILE)) fs.writeFileSync(PORTFOLIO_FILE, '[]');
if (!fs.existsSync(SETTINGS_FILE)) {
  fs.writeFileSync(SETTINGS_FILE, JSON.stringify({
    heroTitle: 'We Build.\nYou Grow.',
    heroSubtitle: 'Crafting world-class websites, web applications, and digital products that elevate brands and accelerate business growth.',
    stats: { projects: 150, satisfaction: 98, years: 12, clients: 85 },
    contactEmail: 'hello@webolite.com',
    contactPhone: '+1 (555) 012-3456',
    updatedAt: new Date().toISOString(),
  }, null, 2));
}

/* ---------- Helpers ---------- */

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.xml': 'application/xml; charset=utf-8',
  '.txt': 'text/plain; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.webp': 'image/webp',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
};

function sendJSON(res, status, data) {
  const body = JSON.stringify(data);
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(body),
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'X-Content-Type-Options': 'nosniff',
  });
  res.end(body);
}

function sendError(res, status, message) {
  sendJSON(res, status, { success: false, error: message });
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    const MAX = 1e6; // 1 MB limit

    req.on('data', (chunk) => {
      size += chunk.length;
      if (size > MAX) {
        reject(new Error('Payload too large'));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });

    req.on('end', () => {
      const raw = Buffer.concat(chunks).toString('utf8');
      if (!raw) return resolve({});
      try {
        resolve(JSON.parse(raw));
      } catch {
        // fallback: try form-urlencoded
        const params = new URLSearchParams(raw);
        const obj = {};
        for (const [k, v] of params) obj[k] = v;
        resolve(obj);
      }
    });

    req.on('error', reject);
  });
}

function readJSON(file) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch {
    return [];
  }
}

function writeJSON(file, data) {
  fs.writeFileSync(file, JSON.stringify(data, null, 2), 'utf8');
}

function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function sanitize(str, max = 2000) {
  if (typeof str !== 'string') return '';
  return str.trim().slice(0, max).replace(/[<>]/g, '');
}

function generateId() {
  return crypto.randomBytes(12).toString('hex');
}

/* ---------- Static file serving ---------- */

function serveStatic(req, res, pathname) {
  let filePath = path.join(ROOT, pathname === '/' ? 'index.html' : pathname);

  // Prevent directory traversal
  if (!filePath.startsWith(ROOT)) {
    sendError(res, 403, 'Forbidden');
    return;
  }

  // Default to index.html for clean URLs
  if (!path.extname(filePath) && !fs.existsSync(filePath)) {
    filePath = path.join(ROOT, 'index.html');
  }

  fs.stat(filePath, (err, stats) => {
    if (err || !stats.isFile()) {
      // SPA-style fallback
      const index = path.join(ROOT, 'index.html');
      fs.readFile(index, (e, data) => {
        if (e) return sendError(res, 404, 'Not found');
        res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
        res.end(data);
      });
      return;
    }

    const ext = path.extname(filePath).toLowerCase();
    const contentType = MIME[ext] || 'application/octet-stream';

    res.writeHead(200, {
      'Content-Type': contentType,
      'Content-Length': stats.size,
      'Cache-Control': ext === '.html' ? 'no-cache' : 'public, max-age=86400',
      'X-Content-Type-Options': 'nosniff',
    });

    fs.createReadStream(filePath).pipe(res);
  });
}

/* ---------- API Routes ---------- */

async function handleContact(req, res) {
  try {
    const body = await readBody(req);

    const name = sanitize(body.name, 100);
    const email = sanitize(body.email, 150).toLowerCase();
    const company = sanitize(body.company || '', 120);
    const budget = sanitize(body.budget || '', 50);
    const message = sanitize(body.message, 3000);

    if (!name) return sendError(res, 400, 'Name is required');
    if (!email) return sendError(res, 400, 'Email is required');
    if (!isValidEmail(email)) return sendError(res, 400, 'Please enter a valid email');
    if (!message) return sendError(res, 400, 'Project details are required');

    const entry = {
      id: generateId(),
      name,
      email,
      company: company || null,
      budget: budget || null,
      message,
      createdAt: new Date().toISOString(),
      ip: req.headers['x-forwarded-for'] || req.socket.remoteAddress || null,
      userAgent: req.headers['user-agent'] || null,
    };

    const contacts = readJSON(CONTACTS_FILE);
    contacts.unshift(entry);
    // Keep last 500
    if (contacts.length > 500) contacts.length = 500;
    writeJSON(CONTACTS_FILE, contacts);

    console.log(`[CONTACT] ${entry.name} <${entry.email}> — ${entry.message.slice(0, 60)}...`);

    sendJSON(res, 201, {
      success: true,
      message: 'Thank you! We received your message and will respond within 24 hours.',
      id: entry.id,
    });
  } catch (err) {
    console.error('[CONTACT ERROR]', err.message);
    sendError(res, 500, 'Something went wrong. Please try again later.');
  }
}

async function handleNewsletter(req, res) {
  try {
    const body = await readBody(req);
    const email = sanitize(body.email || '', 150).toLowerCase();

    if (!email) return sendError(res, 400, 'Email is required');
    if (!isValidEmail(email)) return sendError(res, 400, 'Please enter a valid email');

    const list = readJSON(NEWSLETTER_FILE);
    const exists = list.some((e) => e.email === email);

    if (exists) {
      return sendJSON(res, 200, {
        success: true,
        message: 'You are already subscribed. Thank you!',
      });
    }

    const entry = {
      id: generateId(),
      email,
      createdAt: new Date().toISOString(),
    };

    list.unshift(entry);
    writeJSON(NEWSLETTER_FILE, list);

    console.log(`[NEWSLETTER] New subscriber: ${email}`);

    sendJSON(res, 201, {
      success: true,
      message: 'Successfully subscribed! Welcome aboard.',
    });
  } catch (err) {
    console.error('[NEWSLETTER ERROR]', err.message);
    sendError(res, 500, 'Something went wrong. Please try again later.');
  }
}

function handleHealth(req, res) {
  const contacts = readJSON(CONTACTS_FILE);
  const newsletter = readJSON(NEWSLETTER_FILE);
  const testimonials = readJSON(TESTIMONIALS_FILE);
  sendJSON(res, 200, {
    status: 'ok',
    service: 'Webolite API',
    version: '1.1.0',
    uptime: process.uptime(),
    stats: {
      contacts: contacts.length,
      subscribers: newsletter.length,
      testimonials: testimonials.length,
      approvedReviews: testimonials.filter((t) => t.status === 'approved').length,
    },
    timestamp: new Date().toISOString(),
  });
}

// Optional: simple protected view of submissions (for demo)
function handleAdminContacts(req, res) {
  // In production you'd protect this with auth. For demo we allow it.
  const contacts = readJSON(CONTACTS_FILE);
  sendJSON(res, 200, { success: true, count: contacts.length, data: contacts });
}

/* ---------- Testimonials ---------- */

function handleGetTestimonials(req, res) {
  const all = readJSON(TESTIMONIALS_FILE);
  // Public endpoint only returns approved reviews
  const approved = all
    .filter((t) => t.status === 'approved')
    .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
  sendJSON(res, 200, { success: true, count: approved.length, data: approved });
}

async function handleSubmitTestimonial(req, res) {
  try {
    const body = await readBody(req);

    const name = sanitize(body.name, 80);
    const position = sanitize(body.position || '', 80);
    const company = sanitize(body.company || '', 100);
    const text = sanitize(body.text, 800);
    let rating = parseInt(body.rating, 10);

    if (!name) return sendError(res, 400, 'Name is required');
    if (!text || text.length < 20) return sendError(res, 400, 'Review must be at least 20 characters');
    if (isNaN(rating) || rating < 1 || rating > 5) rating = 5;

    // Generate initials for avatar
    const parts = name.split(/\s+/);
    const avatar = parts.length >= 2
      ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
      : name.slice(0, 2).toUpperCase();

    const entry = {
      id: generateId(),
      name,
      position: position || 'Client',
      company: company || '',
      rating,
      text,
      avatar,
      status: 'pending', // requires approval before showing publicly
      createdAt: new Date().toISOString(),
    };

    const list = readJSON(TESTIMONIALS_FILE);
    list.unshift(entry);
    writeJSON(TESTIMONIALS_FILE, list);

    console.log(`[TESTIMONIAL] New review from ${entry.name} (${entry.rating}★) — pending approval`);

    sendJSON(res, 201, {
      success: true,
      message: 'Thank you for your review! It will appear after moderation.',
      id: entry.id,
    });
  } catch (err) {
    console.error('[TESTIMONIAL ERROR]', err.message);
    sendError(res, 500, 'Something went wrong. Please try again later.');
  }
}

function handleAdminTestimonials(req, res) {
  const all = readJSON(TESTIMONIALS_FILE);
  sendJSON(res, 200, { success: true, count: all.length, data: all });
}

// Approve or reject a testimonial: POST /api/admin/testimonials/:id  { "status": "approved" | "rejected" }
async function handleModerateTestimonial(req, res, id) {
  try {
    const body = await readBody(req);
    const status = (body.status || '').toLowerCase();

    if (!['approved', 'rejected', 'pending'].includes(status)) {
      return sendError(res, 400, 'Status must be approved, rejected, or pending');
    }

    const list = readJSON(TESTIMONIALS_FILE);
    const index = list.findIndex((t) => t.id === id);

    if (index === -1) return sendError(res, 404, 'Testimonial not found');

    list[index].status = status;
    list[index].moderatedAt = new Date().toISOString();
    writeJSON(TESTIMONIALS_FILE, list);

    console.log(`[TESTIMONIAL] ${id} → ${status}`);

    sendJSON(res, 200, {
      success: true,
      message: `Testimonial ${status}`,
      data: list[index],
    });
  } catch (err) {
    console.error('[MODERATE ERROR]', err.message);
    sendError(res, 500, 'Something went wrong');
  }
}

/* ---------- Auth ---------- */

function getToken(req) {
  const auth = req.headers['authorization'] || '';
  if (auth.startsWith('Bearer ')) return auth.slice(7);
  return null;
}

function requireAuth(req, res) {
  const token = getToken(req);
  if (!token || !activeTokens.has(token)) {
    sendError(res, 401, 'Unauthorized. Please log in.');
    return false;
  }
  return true;
}

async function handleLogin(req, res) {
  try {
    const body = await readBody(req);
    if ((body.password || '') !== ADMIN_PASSWORD) {
      return sendError(res, 401, 'Invalid password');
    }
    const token = crypto.randomBytes(32).toString('hex');
    activeTokens.add(token);
    sendJSON(res, 200, { success: true, token, message: 'Logged in' });
  } catch {
    sendError(res, 500, 'Login failed');
  }
}

function handleLogout(req, res) {
  const token = getToken(req);
  if (token) activeTokens.delete(token);
  sendJSON(res, 200, { success: true, message: 'Logged out' });
}

/* ---------- Portfolio API ---------- */

function handleGetPortfolio(req, res) {
  const items = readJSON(PORTFOLIO_FILE);
  sendJSON(res, 200, { success: true, count: items.length, data: items });
}

async function handleCreatePortfolio(req, res) {
  if (!requireAuth(req, res)) return;
  try {
    const body = await readBody(req);
    const title = sanitize(body.title, 120);
    if (!title) return sendError(res, 400, 'Title is required');

    const entry = {
      id: generateId(),
      title,
      category: sanitize(body.category || 'web', 60),
      catLabel: sanitize(body.catLabel || 'Project', 60),
      gradient: sanitize(body.gradient || 'gradient-1', 20),
      tags: Array.isArray(body.tags) ? body.tags.map((t) => sanitize(String(t), 30)).slice(0, 6) : [],
      image: sanitize(body.image || '', 500),
      demoUrl: sanitize(body.demoUrl || '#', 300),
      caseUrl: sanitize(body.caseUrl || '#', 300),
      createdAt: new Date().toISOString(),
    };

    const list = readJSON(PORTFOLIO_FILE);
    list.unshift(entry);
    writeJSON(PORTFOLIO_FILE, list);
    console.log(`[PORTFOLIO] Created: ${entry.title}`);
    sendJSON(res, 201, { success: true, data: entry });
  } catch (err) {
    sendError(res, 500, err.message);
  }
}

async function handleUpdatePortfolio(req, res, id) {
  if (!requireAuth(req, res)) return;
  try {
    const body = await readBody(req);
    const list = readJSON(PORTFOLIO_FILE);
    const idx = list.findIndex((p) => p.id === id);
    if (idx === -1) return sendError(res, 404, 'Project not found');

    const p = list[idx];
    if (body.title !== undefined) p.title = sanitize(body.title, 120);
    if (body.category !== undefined) p.category = sanitize(body.category, 60);
    if (body.catLabel !== undefined) p.catLabel = sanitize(body.catLabel, 60);
    if (body.gradient !== undefined) p.gradient = sanitize(body.gradient, 20);
    if (body.image !== undefined) p.image = sanitize(body.image, 500);
    if (body.demoUrl !== undefined) p.demoUrl = sanitize(body.demoUrl, 300);
    if (body.caseUrl !== undefined) p.caseUrl = sanitize(body.caseUrl, 300);
    if (Array.isArray(body.tags)) p.tags = body.tags.map((t) => sanitize(String(t), 30)).slice(0, 6);
    p.updatedAt = new Date().toISOString();

    writeJSON(PORTFOLIO_FILE, list);
    sendJSON(res, 200, { success: true, data: p });
  } catch (err) {
    sendError(res, 500, err.message);
  }
}

function handleDeletePortfolio(req, res, id) {
  if (!requireAuth(req, res)) return;
  const list = readJSON(PORTFOLIO_FILE);
  const filtered = list.filter((p) => p.id !== id);
  if (filtered.length === list.length) return sendError(res, 404, 'Project not found');
  writeJSON(PORTFOLIO_FILE, filtered);
  sendJSON(res, 200, { success: true, message: 'Deleted' });
}

/* ---------- Settings API ---------- */

function handleGetSettings(req, res) {
  sendJSON(res, 200, { success: true, data: readJSON(SETTINGS_FILE) });
}

async function handleUpdateSettings(req, res) {
  if (!requireAuth(req, res)) return;
  try {
    const body = await readBody(req);
    const current = readJSON(SETTINGS_FILE);
    const updated = {
      ...current,
      ...(body.heroTitle !== undefined && { heroTitle: sanitize(body.heroTitle, 200) }),
      ...(body.heroSubtitle !== undefined && { heroSubtitle: sanitize(body.heroSubtitle, 500) }),
      ...(body.contactEmail !== undefined && { contactEmail: sanitize(body.contactEmail, 150) }),
      ...(body.contactPhone !== undefined && { contactPhone: sanitize(body.contactPhone, 50) }),
      ...(body.stats && {
        stats: {
          projects: parseInt(body.stats.projects, 10) || current.stats?.projects || 0,
          satisfaction: parseInt(body.stats.satisfaction, 10) || current.stats?.satisfaction || 0,
          years: parseInt(body.stats.years, 10) || current.stats?.years || 0,
          clients: parseInt(body.stats.clients, 10) || current.stats?.clients || 0,
        },
      }),
      updatedAt: new Date().toISOString(),
    };
    writeJSON(SETTINGS_FILE, updated);
    sendJSON(res, 200, { success: true, data: updated });
  } catch (err) {
    sendError(res, 500, err.message);
  }
}

/* ---------- Admin delete helpers ---------- */

function handleDeleteContact(req, res, id) {
  if (!requireAuth(req, res)) return;
  const list = readJSON(CONTACTS_FILE);
  const filtered = list.filter((c) => c.id !== id);
  writeJSON(CONTACTS_FILE, filtered);
  sendJSON(res, 200, { success: true, message: 'Deleted' });
}

function handleDeleteTestimonial(req, res, id) {
  if (!requireAuth(req, res)) return;
  const list = readJSON(TESTIMONIALS_FILE);
  const filtered = list.filter((t) => t.id !== id);
  writeJSON(TESTIMONIALS_FILE, filtered);
  sendJSON(res, 200, { success: true, message: 'Deleted' });
}

function handleDeleteNewsletter(req, res, id) {
  if (!requireAuth(req, res)) return;
  const list = readJSON(NEWSLETTER_FILE);
  const filtered = list.filter((n) => n.id !== id);
  writeJSON(NEWSLETTER_FILE, filtered);
  sendJSON(res, 200, { success: true, message: 'Deleted' });
}

function handleAdminNewsletter(req, res) {
  if (!requireAuth(req, res)) return;
  const list = readJSON(NEWSLETTER_FILE);
  sendJSON(res, 200, { success: true, count: list.length, data: list });
}

/* ---------- Router ---------- */

const server = http.createServer(async (req, res) => {
  const parsed = new URL(req.url || '/', `http://${req.headers.host}`);
  const pathname = parsed.pathname;
  const method = req.method;

  // CORS preflight
  if (method === 'OPTIONS') {
    res.writeHead(204, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
      'Access-Control-Max-Age': '86400',
    });
    return res.end();
  }

  // API routes
  if (pathname.startsWith('/api/')) {
    // Public
    if (pathname === '/api/health' && method === 'GET') return handleHealth(req, res);
    if (pathname === '/api/contact' && method === 'POST') return handleContact(req, res);
    if (pathname === '/api/newsletter' && method === 'POST') return handleNewsletter(req, res);
    if (pathname === '/api/testimonials' && method === 'GET') return handleGetTestimonials(req, res);
    if (pathname === '/api/testimonials' && method === 'POST') return handleSubmitTestimonial(req, res);
    if (pathname === '/api/portfolio' && method === 'GET') return handleGetPortfolio(req, res);
    if (pathname === '/api/settings' && method === 'GET') return handleGetSettings(req, res);

    // Auth
    if (pathname === '/api/admin/login' && method === 'POST') return handleLogin(req, res);
    if (pathname === '/api/admin/logout' && method === 'POST') return handleLogout(req, res);

    // Admin — contacts
    if (pathname === '/api/admin/contacts' && method === 'GET') {
      if (!requireAuth(req, res)) return;
      return handleAdminContacts(req, res);
    }
    if (pathname.startsWith('/api/admin/contacts/') && method === 'DELETE') {
      return handleDeleteContact(req, res, pathname.split('/').pop());
    }

    // Admin — testimonials
    if (pathname === '/api/admin/testimonials' && method === 'GET') {
      if (!requireAuth(req, res)) return;
      return handleAdminTestimonials(req, res);
    }
    if (pathname.startsWith('/api/admin/testimonials/') && method === 'POST') {
      if (!requireAuth(req, res)) return;
      return handleModerateTestimonial(req, res, pathname.split('/').pop());
    }
    if (pathname.startsWith('/api/admin/testimonials/') && method === 'DELETE') {
      return handleDeleteTestimonial(req, res, pathname.split('/').pop());
    }

    // Admin — newsletter
    if (pathname === '/api/admin/newsletter' && method === 'GET') return handleAdminNewsletter(req, res);
    if (pathname.startsWith('/api/admin/newsletter/') && method === 'DELETE') {
      return handleDeleteNewsletter(req, res, pathname.split('/').pop());
    }

    // Admin — portfolio
    if (pathname === '/api/admin/portfolio' && method === 'POST') return handleCreatePortfolio(req, res);
    if (pathname.startsWith('/api/admin/portfolio/') && method === 'PUT') {
      return handleUpdatePortfolio(req, res, pathname.split('/').pop());
    }
    if (pathname.startsWith('/api/admin/portfolio/') && method === 'DELETE') {
      return handleDeletePortfolio(req, res, pathname.split('/').pop());
    }

    // Admin — settings
    if (pathname === '/api/admin/settings' && method === 'PUT') return handleUpdateSettings(req, res);

    return sendError(res, 404, 'API endpoint not found');
  }

  // Static files
  if (method === 'GET' || method === 'HEAD') {
    return serveStatic(req, res, pathname);
  }

  sendError(res, 405, 'Method not allowed');
});

/* ---------- Start ---------- */

server.listen(PORT, HOST, () => {
  console.log('');
  console.log('  ╔══════════════════════════════════════════╗');
  console.log('  ║         Webolite Fullstack Server        ║');
  console.log('  ╚══════════════════════════════════════════╝');
  console.log(`  → Local:   http://localhost:${PORT}`);
  console.log(`  → Network: http://${HOST}:${PORT}`);
  console.log('');
  console.log('  API Endpoints:');
  console.log('    GET  /api/health');
  console.log('    POST /api/contact');
  console.log('    POST /api/newsletter');
  console.log('    GET  /api/testimonials');
  console.log('    POST /api/testimonials');
  console.log('    GET  /api/admin/contacts');
  console.log('    GET  /api/admin/testimonials');
  console.log('    POST /api/admin/testimonials/:id');
  console.log('');
  console.log('  Press Ctrl+C to stop');
  console.log('');
});

process.on('SIGINT', () => {
  console.log('\n  Shutting down Webolite server...');
  server.close(() => process.exit(0));
});
