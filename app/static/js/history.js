"use strict";
// History page: loads /api/history for the selected window and draws three
// charts (bandwidth, circuits, connections).

const RANGE_SEC = { "1h": 3600, "6h": 21600, "24h": 86400, "7d": 604800 };
let currentRange = "24h";
let refreshTimer = null;

async function load() {
  let data;
  try {
    const r = await fetch("/api/history?range=" + currentRange, { credentials: "same-origin" });
    if (r.status === 401) { location.href = "/login"; return; }
    data = await r.json();
  } catch (e) { return; }

  const pts = data.points || [];
  const rangeSec = RANGE_SEC[currentRange] || 86400;
  const empty = document.getElementById("bwEmpty");
  empty.classList.toggle("hidden", pts.length > 1);

  TorChart.drawLineChart(document.getElementById("bwChart"), {
    rangeSec,
    yFormat: TorChart.fmtBytesPerSec,
    series: [
      { data: pts.map(p => ({ t: p.t, v: p.down })), color: "#a368c4" },
      { data: pts.map(p => ({ t: p.t, v: p.up })), color: "#3fb950" },
    ],
  });

  TorChart.drawLineChart(document.getElementById("circChart"), {
    rangeSec,
    yFormat: v => String(Math.round(v)),
    series: [{ data: pts.map(p => ({ t: p.t, v: p.circuits })), color: "#d9a441" }],
  });

  TorChart.drawLineChart(document.getElementById("connChart"), {
    rangeSec,
    yFormat: v => String(Math.round(v)),
    series: [{ data: pts.map(p => ({ t: p.t, v: p.connections })), color: "#4ea1d3" }],
  });
}

document.getElementById("rangeTabs").addEventListener("click", (e) => {
  const btn = e.target.closest("[data-range]");
  if (!btn) return;
  currentRange = btn.dataset.range;
  document.querySelectorAll(".range-tab").forEach(b => b.classList.toggle("active", b === btn));
  load();
});

window.addEventListener("resize", () => load());
load();
refreshTimer = setInterval(load, 30000);
