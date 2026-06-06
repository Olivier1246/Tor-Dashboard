"use strict";
// Mini moteur de graphique linéaire sur canvas — sans dépendance (compatible
// onion service hors-ligne). Gère plusieurs séries, axe temporel, grille,
// libellés d'axe Y formatables, et coupures de courbe sur valeurs nulles.

const ChartColors = {
  grid: "#36294a",
  axis: "#9b8fb0",
  text: "#9b8fb0",
};

function niceMax(v) {
  if (v <= 0) return 1;
  const pow = Math.pow(10, Math.floor(Math.log10(v)));
  const n = v / pow;
  const step = n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10;
  return step * pow;
}

function fmtTimeLabel(ts, rangeSec) {
  const d = new Date(ts * 1000);
  const p = (x) => String(x).padStart(2, "0");
  if (rangeSec > 86400 * 2) return `${p(d.getDate())}/${p(d.getMonth() + 1)}`;
  return `${p(d.getHours())}:${p(d.getMinutes())}`;
}

// opts: { yFormat(v)->str, rangeSec, series:[{data:[{t,v}], color}] }
function drawLineChart(canvas, opts) {
  const dpr = window.devicePixelRatio || 1;
  const W = canvas.clientWidth || 600;
  const H = parseInt(canvas.getAttribute("height"), 10) || 200;
  canvas.width = W * dpr;
  canvas.height = H * dpr;
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, W, H);

  const padL = 64, padR = 12, padT = 12, padB = 26;
  const plotW = W - padL - padR;
  const plotH = H - padT - padB;

  // Domaine X (temps) et Y (max sur toutes séries)
  let tMin = Infinity, tMax = -Infinity, vMax = 0;
  for (const s of opts.series) {
    for (const p of s.data) {
      if (p.t < tMin) tMin = p.t;
      if (p.t > tMax) tMax = p.t;
      if (p.v != null && p.v > vMax) vMax = p.v;
    }
  }
  if (!isFinite(tMin) || tMax === tMin) {
    ctx.fillStyle = ChartColors.text;
    ctx.font = "13px system-ui";
    ctx.fillText("Données insuffisantes", padL, padT + plotH / 2);
    return;
  }
  vMax = niceMax(vMax);

  const x = (t) => padL + ((t - tMin) / (tMax - tMin)) * plotW;
  const y = (v) => padT + plotH - (v / vMax) * plotH;

  // Grille + libellés Y
  ctx.font = "11px system-ui";
  ctx.textBaseline = "middle";
  const yTicks = 4;
  for (let i = 0; i <= yTicks; i++) {
    const v = (vMax / yTicks) * i;
    const yy = y(v);
    ctx.strokeStyle = ChartColors.grid;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(padL, yy);
    ctx.lineTo(W - padR, yy);
    ctx.stroke();
    ctx.fillStyle = ChartColors.text;
    ctx.textAlign = "right";
    ctx.fillText(opts.yFormat ? opts.yFormat(v) : String(Math.round(v)), padL - 8, yy);
  }

  // Libellés X (5 repères)
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  const xTicks = 5;
  for (let i = 0; i <= xTicks; i++) {
    const t = tMin + ((tMax - tMin) / xTicks) * i;
    ctx.fillStyle = ChartColors.text;
    ctx.fillText(fmtTimeLabel(t, opts.rangeSec), x(t), H - padB + 6);
  }

  // Séries
  for (const s of opts.series) {
    // Aire douce
    ctx.beginPath();
    let started = false;
    for (const p of s.data) {
      if (p.v == null) { started = false; continue; }
      const px = x(p.t), py = y(p.v);
      if (!started) { ctx.moveTo(px, py); started = true; }
      else ctx.lineTo(px, py);
    }
    ctx.strokeStyle = s.color;
    ctx.lineWidth = 2;
    ctx.lineJoin = "round";
    ctx.stroke();

    // Remplissage léger sous la courbe (par segments continus)
    ctx.save();
    ctx.globalAlpha = 0.12;
    ctx.beginPath();
    started = false;
    let segStartX = null, lastX = null;
    for (const p of s.data) {
      if (p.v == null) {
        if (started) { ctx.lineTo(lastX, y(0)); ctx.lineTo(segStartX, y(0)); ctx.closePath(); ctx.fillStyle = s.color; ctx.fill(); ctx.beginPath(); started = false; }
        continue;
      }
      const px = x(p.t), py = y(p.v);
      if (!started) { ctx.moveTo(px, y(0)); ctx.lineTo(px, py); segStartX = px; started = true; }
      else ctx.lineTo(px, py);
      lastX = px;
    }
    if (started) { ctx.lineTo(lastX, y(0)); ctx.lineTo(segStartX, y(0)); ctx.closePath(); ctx.fillStyle = s.color; ctx.fill(); }
    ctx.restore();
  }
}

function fmtBytesPerSec(v) {
  if (v == null) return "0";
  const u = ["o", "K", "M", "G", "T"];
  let i = 0;
  while (v >= 1024 && i < u.length - 1) { v /= 1024; i++; }
  return (i === 0 ? Math.round(v) : v.toFixed(1)) + " " + u[i] + "o/s";
}

window.TorChart = { drawLineChart, fmtBytesPerSec };
