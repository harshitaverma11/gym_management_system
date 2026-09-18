/**
 * GymPro — js/script.js
 * Place this file at: Gym_Management_System/js/script.js
 */

const API_BASE_URL = 'http://127.0.0.1:5000';

// ── User helpers ──────────────────────────────────────────────────────────────

function getCurrentUser() {
  try { return JSON.parse(localStorage.getItem('gymUser')) || null; }
  catch(e) { return null; }
}

function setCurrentUser(user) {
  localStorage.setItem('gymUser',     JSON.stringify(user));
  localStorage.setItem('currentUser', JSON.stringify(user));
}

function clearCurrentUser() {
  localStorage.removeItem('gymUser');
  localStorage.removeItem('currentUser');
}

function getCurrentRole() {
  var u = getCurrentUser();
  return u ? u.role : null;
}

// ── apiFetch — THE MAIN FUNCTION ──────────────────────────────────────────────
// Always sends X-User header. Use this instead of raw fetch() for all API calls.

function apiFetch(path, options) {
  var opts    = options || {};
  var user    = getCurrentUser();
  var headers = {};

  // copy any existing headers
  if (opts.headers) {
    if (typeof opts.headers.forEach === 'function') {
      opts.headers.forEach(function(v, k) { headers[k] = v; });
    } else {
      Object.keys(opts.headers).forEach(function(k) {
        headers[k] = opts.headers[k];
      });
    }
  }

  // set content-type for POST/PUT
  if (!headers['Content-Type'] && opts.body) {
    headers['Content-Type'] = 'application/json';
  }

  // inject X-User — this is what fixes the 401
  if (user) {
    headers['X-User'] = JSON.stringify(user);
  }

  return fetch(API_BASE_URL + path, {
    credentials: 'include',
    method:      opts.method  || 'GET',
    body:        opts.body    || undefined,
    headers:     headers,
  });
}

// ── Route protection ──────────────────────────────────────────────────────────

(function() {
  var publicPages = ['', 'index.html', 'login.html', 'debug_test.html'];
  var current     = window.location.pathname.split('/').pop();
  if (publicPages.indexOf(current) === -1 && !getCurrentUser()) {
    window.location.href = 'login.html';
  }
})();

function requireAuth() {
  if (!getCurrentUser()) window.location.href = 'login.html';
}

function requireRole(roles) {
  var role = getCurrentRole();
  if (!role || roles.indexOf(role) === -1) {
    clearCurrentUser();
    window.location.href = 'login.html';
  }
}

function adjustUIForRole() {
  var role = getCurrentRole();
  if (!role) return;
  document.querySelectorAll('[data-role]').forEach(function(el) {
    var allowed = el.getAttribute('data-role').split(',').map(function(s) { return s.trim(); });
    if (allowed.indexOf(role) === -1) el.style.display = 'none';
  });
}

// ── Logout ────────────────────────────────────────────────────────────────────

function logout() {
  apiFetch('/logout', { method: 'POST' })
    .catch(function() {})
    .finally(function() {
      clearCurrentUser();
      window.location.href = 'login.html';
    });
}

// ── Theme ─────────────────────────────────────────────────────────────────────

function applyStoredTheme() {
  var t   = localStorage.getItem('gymTheme') || 'dark';
  document.documentElement.setAttribute('data-theme', t);
  var btn = document.getElementById('themeBtn');
  if (btn) btn.textContent = t === 'dark' ? '🌜' : '🌞';
}

function toggleTheme() {
  var html = document.documentElement;
  var dark = html.getAttribute('data-theme') === 'dark';
  html.setAttribute('data-theme', dark ? 'light' : 'dark');
  localStorage.setItem('gymTheme', dark ? 'light' : 'dark');
  var btn = document.getElementById('themeBtn');
  if (btn) btn.textContent = dark ? '🌞' : '🌜';
}

// ── Notification ──────────────────────────────────────────────────────────────

function showNotification(message, type) {
  var el = document.getElementById('notification');
  if (!el) return;
  el.textContent = message;
  el.className   = 'notification ' + (type || 'success') + ' show';
  setTimeout(function() { el.classList.remove('show'); }, 3000);
}

// ── Formatters ────────────────────────────────────────────────────────────────

function formatINR(n) {
  n = parseFloat(n) || 0;
  if (n >= 100000) return '₹' + (n / 100000).toFixed(1) + 'L';
  if (n >= 1000)   return '₹' + (n / 1000).toFixed(1) + 'K';
  return '₹' + n.toFixed(0);
}

function formatDate(d) {
  var dt = new Date(d);
  if (isNaN(dt)) return d || '—';
  return dt.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}
