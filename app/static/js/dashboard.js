"use strict";
// Dashboard: periodic polling of /api/metrics, rate computation from the
// cumulative counters, and canvas sparkline rendering.

const POLL_MS = 3000;
const HISTORY = 40;

const histDown = [];
const histUp = [];
let prev = null; // { t, read, written }

function fmtBytes(n) {
  if (n == null || isNaN(n)) return "—";
  const u = ["B", "KB", "MB", "GB", "TB", "PB"];
  let i = 0;
  n = Number(n);
  while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
  return n.toFixed(i === 0 ? 0 : 1) + " " + u[i];
}

function fmtRate(bytesPerSec) {
  if (bytesPerSec == null || isNaN(bytesPerSec)) return "—";
  return fmtBytes(bytesPerSec);
}

function fmtUptime(s) {
  if (s == null) return "—";
  const d = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  const m = Math.floor((s % 3600) / 60);
  if (d > 0) return `${d}d ${h}h ${m}m`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function drawSpark(canvasId, data, color) {
  const c = document.getElementById(canvasId);
  if (!c) return;
  const dpr = window.devicePixelRatio || 1;
  const w = c.clientWidth || 200;
  const h = c.height;
  c.width = w * dpr;
  c.height = h * dpr;
  const ctx = c.getContext("2d");
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, w, h);
  if (data.length < 2) return;
  const max = Math.max(...data, 1);
  const step = w / (HISTORY - 1);
  ctx.beginPath();
  data.forEach((v, i) => {
    const x = i * step;
    const y = h - (v / max) * (h - 4) - 2;
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  });
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.lineJoin = "round";
  ctx.stroke();
  // soft fill
  ctx.lineTo((data.length - 1) * step, h);
  ctx.lineTo(0, h);
  ctx.closePath();
  ctx.fillStyle = color + "22";
  ctx.fill();
}

function setOnline(online) {
  const pill = document.getElementById("statusPill");
  const banner = document.getElementById("offlineBanner");
  if (pill) {
    pill.classList.toggle("online", online);
    pill.classList.toggle("offline", !online);
  }
  setText("statusText", online ? "Relay online" : "Relay offline");
  if (banner) banner.classList.toggle("hidden", online);
}

function renderFlags(flags) {
  const box = document.getElementById("flags");
  if (!box) return;
  if (!flags || flags.length === 0) {
    box.innerHTML = '<span class="muted">No flags (relay not yet published?)</span>';
    return;
  }
  box.innerHTML = flags.map(f => `<span class="flag">${f}</span>`).join("");
}

function renderAccounting(a) {
  const body = document.getElementById("acctBody");
  if (!body) return;
  if (!a || !a.enabled) {
    body.innerHTML = '<p class="muted">No accounting limit configured.</p>';
    return;
  }
  const usedR = a.read_used || 0, usedW = a.written_used || 0;
  const leftR = a.read_left || 0, leftW = a.written_left || 0;
  const totR = usedR + leftR, totW = usedW + leftW;
  const pct = totR + totW > 0
    ? Math.round(((usedR + usedW) / (totR + totW)) * 100) : 0;
  body.innerHTML = `
    <div class="acct-bar"><div style="width:${pct}%"></div></div>
    <dl class="kv">
      <dt>Used</dt><dd>${fmtBytes(usedR + usedW)} (${pct}%)</dd>
      <dt>Remaining</dt><dd>${fmtBytes(leftR + leftW)}</dd>
      <dt>Period end</dt><dd>${a.interval_end || "—"}</dd>
      <dt>Hibernating</dt><dd>${a.hibernating || "—"}</dd>
    </dl>`;
}

async function tick() {
  let m;
  try {
    const r = await fetch("/api/metrics", { credentials: "same-origin" });
    if (r.status === 401) { location.href = "/login"; return; }
    m = await r.json();
  } catch (e) {
    setOnline(false);
    return;
  }

  if (!m.online) { setOnline(false); return; }
  setOnline(true);

  // Rates from the deltas of the cumulative counters
  const now = Date.now() / 1000;
  if (prev) {
    const dt = Math.max(now - prev.t, 0.5);
    const down = Math.max((m.read_total - prev.read) / dt, 0);
    const up = Math.max((m.written_total - prev.written) / dt, 0);
    setText("rateDown", fmtRate(down));
    setText("rateUp", fmtRate(up));
    histDown.push(down); if (histDown.length > HISTORY) histDown.shift();
    histUp.push(up); if (histUp.length > HISTORY) histUp.shift();
    drawSpark("sparkDown", histDown, "#a368c4");
    drawSpark("sparkUp", histUp, "#3fb950");
  }
  prev = { t: now, read: m.read_total, written: m.written_total };

  setText("uptime", fmtUptime(m.uptime));
  setText("bootstrap", m.bootstrap ?? "—");
  setText("circuits", m.circuits ?? "—");
  setText("connections", m.connections ?? "—");
  setText("nickname", m.nickname || "—");
  setText("fingerprint", m.fingerprint || "—");
  setText("version", m.version || "—");
  setText("onion", m.onion || "not published");
  setText("readTotal", fmtBytes(m.read_total));
  setText("writtenTotal", fmtBytes(m.written_total));
  setText("confRate", m.rate ? fmtBytes(m.rate) + "/s" : "unlimited");
  setText("confBurst", m.burst ? fmtBytes(m.burst) + "/s" : "unlimited");
  setText("exitPolicy", m.exit_policy || "—");
  renderFlags(m.flags);
  renderAccounting(m.accounting);
}

tick();
setInterval(tick, POLL_MS);
