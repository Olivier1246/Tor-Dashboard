"use strict";
// Connections page: aggregates OR peers by country via /api/connections.

function setText(id, v) { const el = document.getElementById(id); if (el) el.textContent = v; }

function setStatus(online) {
  const pill = document.getElementById("connPill");
  pill.classList.toggle("online", online);
  pill.classList.toggle("offline", !online);
  setText("connStatus", online ? "Relay online" : "Relay offline");
}

function render(data) {
  const list = document.getElementById("countryList");
  const countries = data.countries || [];
  setText("kTotal", data.total ?? "—");
  setText("kCountries", countries.length);
  setText("kResolved", data.resolved ?? "—");
  setText("kUnresolved", data.unresolved ?? "—");

  if (!countries.length) {
    list.innerHTML = '<p class="muted">No active OR connection at the moment.</p>';
    return;
  }
  const max = countries[0].count || 1;
  list.innerHTML = countries.map(c => `
    <div class="country-row">
      <span class="cflag">${c.flag}</span>
      <span class="cname">${c.name}</span>
      <span class="cbar"><i style="width:${Math.max(2, (c.count / max) * 100)}%"></i></span>
      <span class="ccount">${c.count}</span>
      <span class="cpct">${c.percent}%</span>
    </div>`).join("");
}

async function load() {
  let data;
  try {
    const r = await fetch("/api/connections", { credentials: "same-origin" });
    if (r.status === 401) { location.href = "/login"; return; }
    data = await r.json();
  } catch (e) { setStatus(false); return; }

  if (!data.online) {
    setStatus(false);
    document.getElementById("countryList").innerHTML =
      '<p class="muted">Relay offline — connections unavailable.</p>';
    return;
  }
  setStatus(true);
  render(data);
}

load();
setInterval(load, 15000);
