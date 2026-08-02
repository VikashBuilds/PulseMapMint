"use strict";

const CATEGORY_LABELS = {
  tech: "TECH", world: "WORLD", finance: "FINANCE", crypto: "CRYPTO",
  markets: "MARKETS", science: "SCIENCE", geohazard: "GEOLOGICAL",
  weather: "WEATHER", github: "GITHUB", social: "SOCIAL",
  startups: "STARTUPS", video: "VIDEO",
};

const RUNNER_LABELS = {
  hn_top: "HN Top", hn_best: "HN Best", hn_ask_show: "HN Ask+Show",
  reddit_all: "Reddit r/all", reddit_world_science: "Reddit World/Sci",
  reddit_tech_startups: "Reddit Tech", reddit_finance_crypto: "Reddit Finance",
  github_all: "GitHub All", github_python_ts: "GitHub Py/TS",
  rss_world: "RSS World", rss_tech: "RSS Tech/AI", rss_finance: "RSS Finance",
  rss_science_space: "RSS Science", crypto_anomalies: "Crypto",
  stocks_movers: "Stocks", usgs_quakes: "USGS Quakes", weather_alerts: "Weather",
  youtube_trending: "YouTube", twitter_x_trends: "X Trends", producthunt_launches: "Product Hunt",
};

const state = { all: null, meta: null, history: null, filter: new Set(), search: "", sort: "heat" };

const $ = (id) => document.getElementById(id);

async function loadJSON(url, altUrl) {
  for (const u of [url, altUrl].filter(Boolean)) {
    try {
      const r = await fetch(u, { cache: "no-store" });
      if (!r.ok) throw new Error(`${r.status} ${u}`);
      return r.json();
    } catch (e) { /* try next */ }
  }
  throw new Error(`unreachable ${url}`);
}

function ago(iso) {
  const t = (new Date(iso)).getTime();
  if (!t) return "?";
  const s = Math.max(0, (Date.now() - t) / 1000);
  if (s < 60) return `${Math.floor(s)}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

function esc(s) {
  const d = document.createElement("div");
  d.textContent = s == null ? "" : String(s);
  return d.innerHTML;
}

function heatColor(h) {
  if (h >= 80) return "var(--red)";
  if (h >= 60) return "var(--amber)";
  return "var(--cyan)";
}

/* ---------------- clock ---------------- */
function tickClock() {
  const d = new Date();
  $("clock").textContent = d.toISOString().slice(11, 19) + " UTC";
}
setInterval(tickClock, 1000);

/* ---------------- ticker ---------------- */
function renderTicker() {
  const items = (state.all?.items || []).slice(0, 18);
  const track = $("ticker-track");
  track.innerHTML = "";
  items.forEach((it, i) => {
    const s = document.createElement("span");
    s.innerHTML = `<b>${String(i + 1).padStart(2, "0")}.</b> ${esc(it.title)}`;
    track.appendChild(s);
  });
}

/* ---------------- runners ---------------- */
function renderRunners() {
  const meta = state.meta;
  const grid = $("runners");
  grid.innerHTML = "";
  const names = Object.keys(meta?.runners || {});
  if (!names.length) {
    grid.innerHTML = '<div class="dim" style="grid-column:span 2;padding:14px">NO TELEMETRY YET</div>';
    return;
  }
  for (const id of names) {
    const r = meta.runners[id];
    const el = document.createElement("div");
    el.className = `runner ${r.status}`;
    const statusText = r.status === "ok" ? "ONLINE" : r.status === "empty" ? "SILENT" : r.status === "skipped" ? "KEY NEEDED" : "FAULT";
    el.innerHTML = `
      <div class="r-name"><span class="r-dot"></span>${esc(RUNNER_LABELS[id] || id)}</div>
      <div class="r-meta"><span>${r.items} EVENTS</span><span class="r-status">${statusText}</span></div>
      ${r.error ? `<div class="r-meta" title="${esc(r.error)}">${esc(r.error.slice(0, 40))}</div>` : ""}`;
    grid.appendChild(el);
  }
}

/* ---------------- stats ---------------- */
function renderStats() {
  const m = state.meta;
  if (!m) return;
  $("stat-events").textContent = m.total_events ?? "-";
  $("stat-breakers").textContent = m.breakers ?? "-";
  const ok = Object.values(m.runners || {}).filter((r) => r.status === "ok").length;
  $("stat-runners").textContent = `${ok}/${Object.keys(m.runners || {}).length}`;
  $("stat-cats").textContent = Object.keys(m.categories || {}).length;
  $("stat-sweeps").textContent = state.history?.length ?? "-";
  $("last-run").textContent = `LAST SWEEP: ${ago(m.generated)}`;
  $("footer-note").textContent = `GENERATED ${m.generated} · SWEEP ${m.ts}`;
}

/* ---------------- feed ---------------- */
function renderFilters() {
  const wrap = $("cat-filters");
  wrap.innerHTML = "";
  const counts = state.meta?.categories || {};
  const cats = Object.keys(CATEGORY_LABELS).filter((c) => counts[c]);
  const allChip = document.createElement("button");
  allChip.className = "cat-chip active";
  allChip.textContent = `ALL (${(state.all?.items || []).length})`;
  allChip.onclick = () => { state.filter.clear(); applyFilterUI(allChip, wrap); renderFeed(); };
  wrap.appendChild(allChip);
  for (const c of cats) {
    const chip = document.createElement("button");
    chip.className = "cat-chip";
    chip.textContent = `${CATEGORY_LABELS[c]} (${counts[c]})`;
    chip.onclick = () => {
      if (state.filter.has(c)) state.filter.delete(c); else state.filter.add(c);
      applyFilterUI(chip, wrap);
      renderFeed();
    };
    wrap.appendChild(chip);
  }
  const all = wrap.querySelector(".cat-chip.active");
  if (all) all.classList.remove("active");
}

function applyFilterUI(chip, wrap) {
  wrap.querySelectorAll(".cat-chip").forEach((c) => c.classList.toggle("active", c === chip));
}

function renderFeed() {
  const q = state.search.toLowerCase();
  let items = (state.all?.items || []).filter((it) => {
    if (state.filter.size && !state.filter.has(it.category)) return false;
    if (q && !(it.title || "").toLowerCase().includes(q) && !(it.source || "").toLowerCase().includes(q)) return false;
    return true;
  });
  if (state.sort === "new") items = [...items].sort((a, b) => (b.published || "").localeCompare(a.published || ""));
  const feed = $("feed");
  feed.innerHTML = "";
  $("feed-empty").classList.toggle("hidden", items.length > 0);
  for (const it of items.slice(0, 80)) {
    const metrics = it.metrics || {};
    const extra = Object.entries(metrics).slice(0, 4).map(([k, v]) => `${k.toUpperCase()}: ${v ?? "-"}`).join(" · ");
    const el = document.createElement("div");
    el.className = `event${it.heat >= 70 ? " breaker" : ""}`;
    el.innerHTML = `
      <a class="event-title" href="${esc(it.url)}" target="_blank" rel="noopener">${esc(it.title)}</a>
      <div class="event-meta">
        <span class="badge cat-${esc(it.category)}">${CATEGORY_LABELS[it.category] || it.category.toUpperCase()}</span>
        <span class="heat-val">HEAT ${it.heat}</span>
        <span>SRC: ${esc(RUNNER_LABELS[it.source] || it.source)}</span>
        <span>${ago(it.published)}</span>
        ${extra ? `<span class="dim">${esc(extra)}</span>` : ""}
      </div>
      <div class="heatbar"><div style="width:${it.heat}%;background:${heatColor(it.heat)}"></div></div>`;
    feed.appendChild(el);
  }
}

/* ---------------- crypto ---------------- */
function renderCrypto() {
  const tbody = $("crypto-body");
  tbody.innerHTML = "";
  const prices = (state.history || []).map((h) => h.prices || {});
  const watch = state.meta?.watch || {};
  const rows = Object.entries(watch).map(([sym, w]) => {
    const series = prices.map((p) => p[sym]?.price).filter((v) => typeof v === "number");
    return { sym, ...w, series };
  }).sort((a, b) => (a.series.length - b.series.length));
  for (const r of rows) {
    const tr = document.createElement("tr");
    const up = r.pct24h >= 0;
    tr.innerHTML = `
      <td>${esc(r.sym.toUpperCase())}</td>
      <td>$${fmt(r.price)}</td>
      <td class="${up ? "up" : "down"}">${(r.pct24h ?? 0).toFixed(2)}%</td>
      <td><canvas width="64" height="22" data-series="${esc(JSON.stringify(r.series))}"></canvas></td>`;
    tbody.appendChild(tr);
  }
  tbody.querySelectorAll("canvas").forEach((cv) => {
    const series = JSON.parse(cv.dataset.series);
    drawSpark(cv, series);
  });
}

function fmt(v) {
  if (v == null) return "-";
  return v >= 100 ? Math.round(v).toLocaleString() : Number(v).toFixed(v < 1 ? 4 : 2);
}

function drawSpark(cv, series) {
  const ctx = cv.getContext("2d");
  ctx.clearRect(0, 0, cv.width, cv.height);
  if (series.length < 2) return;
  const min = Math.min(...series), max = Math.max(...series);
  const span = max - min || 1;
  ctx.beginPath();
  series.forEach((v, i) => {
    const x = (i / (series.length - 1)) * (cv.width - 4) + 2;
    const y = cv.height - 2 - ((v - min) / span) * (cv.height - 4);
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  });
  ctx.strokeStyle = series[series.length - 1] >= series[0] ? "var(--green)" : "var(--red)";
  ctx.lineWidth = 1.4;
  ctx.stroke();
}

/* ---------------- earthquakes ---------------- */
function renderQuakes() {
  const items = (state.all?.items || []).filter((it) => it.category === "geohazard");
  const list = $("quake-list");
  list.innerHTML = "";
  $("quake-count").textContent = `(${items.length})`;
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 640 320");
  svg.innerHTML = `
    <rect x="0" y="0" width="640" height="320" fill="#04070f"/>
    ${Array.from({ length: 11 }, (_, i) => `<line x1="0" y1="${(i + 1) * 26.6}" x2="640" y2="${(i + 1) * 26.6}" stroke="#0f1c33" stroke-width="1"/>`).join("")}
    ${Array.from({ length: 15 }, (_, i) => `<line x1="${(i + 1) * 40}" y1="0" x2="${(i + 1) * 40}" y2="320" stroke="#0f1c33" stroke-width="1"/>`).join("")}
    <rect x="0" y="0" width="640" height="320" fill="none" stroke="#1b2a45"/>`;
  for (const it of items.slice(0, 30)) {
    const m = it.metrics || {};
    if (m.lat == null || m.lon == null) continue;
    const x = ((m.lon + 180) / 360) * 640;
    const y = ((90 - m.lat) / 180) * 320;
    const cls = (m.mag || 0) >= 6 ? "lg" : (m.mag || 0) >= 5 ? "md" : "sm";
    const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    dot.setAttribute("cx", x); dot.setAttribute("cy", y);
    dot.setAttribute("class", `map-dot ${cls}`);
    dot.setAttribute("r", cls === "lg" ? 5 : cls === "md" ? 3.6 : 2.4);
    dot.innerHTML = `<title>${esc(it.title)}</title>`;
    svg.appendChild(dot);
  }
  $("quake-map").innerHTML = "";
  $("quake-map").appendChild(svg);
  const sorted = [...items].sort((a, b) => (b.metrics?.mag || 0) - (a.metrics?.mag || 0));
  for (const it of sorted.slice(0, 8)) {
    const li = document.createElement("li");
    li.innerHTML = `<span class="mag">M${(it.metrics?.mag ?? 0).toFixed(1)}</span><a href="${esc(it.url)}" target="_blank" rel="noopener">${esc(it.title)}</a>`;
    list.appendChild(li);
  }
}

/* ---------------- weather ---------------- */
function renderWeather() {
  const items = (state.all?.items || []).filter((it) => it.category === "weather");
  const wrap = $("weather");
  wrap.innerHTML = "";
  if (!items.length) { wrap.innerHTML = '<div class="dim" style="padding:12px">NO ACTIVE ALERTS</div>'; return; }
  for (const it of items.slice(0, 6)) {
    const sev = (it.metrics?.severity || "yellow").toLowerCase();
    const card = document.createElement("div");
    card.className = `w-card ${sev}`;
    card.innerHTML = `
      <div class="w-event">${esc(it.title)}</div>
      <div class="w-meta"><span class="sev-${sev}">${esc(sev.toUpperCase())}</span> · ${ago(it.published)}</div>
      ${it.metrics?.description ? `<div class="w-meta">${esc(it.metrics.description)}</div>` : ""}`;
    wrap.appendChild(card);
  }
}

/* ---------------- pulse chart ---------------- */
function renderPulse() {
  const cv = $("pulse-chart");
  const ctx = cv.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const W = cv.clientWidth, H = 120;
  cv.width = W * dpr; cv.height = H * dpr;
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, W, H);
  const hist = (state.history || []).slice(-48);
  if (!hist.length) return;
  ctx.strokeStyle = "#1b2a45";
  ctx.beginPath();
  ctx.moveTo(0, H / 2); ctx.lineTo(W, H / 2);
  ctx.stroke();
  const maxEv = Math.max(...hist.map((h) => h.events), 1);
  ctx.strokeStyle = "var(--cyan)";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  hist.forEach((h, i) => {
    const x = (i / (hist.length - 1)) * W;
    const y = H - 6 - (h.events / maxEv) * (H - 14);
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  });
  ctx.stroke();
  ctx.strokeStyle = "var(--magenta)";
  ctx.beginPath();
  hist.forEach((h, i) => {
    const x = (i / (hist.length - 1)) * W;
    const y = H - 6 - (h.avg_heat / 100) * (H - 14);
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  });
  ctx.stroke();
}

/* ---------------- boot ---------------- */
async function refresh() {
  try {
    const [all, meta, history] = await Promise.all([
      loadJSON("data/latest/all.json", "../data/latest/all.json"),
      loadJSON("data/latest/meta.json", "../data/latest/meta.json"),
      loadJSON("data/history.json", "../data/history.json"),
    ]);
    state.all = all; state.meta = meta; state.history = history;
    renderTicker(); renderRunners(); renderStats(); renderFilters();
    renderFeed(); renderCrypto(); renderQuakes(); renderWeather(); renderPulse();
  } catch (e) {
    $("feed").innerHTML = `<div class="feed-empty">DATA LINK FAILED: ${esc(e.message)}<br><br>RUN <b>scripts/run_all.py</b> LOCALLY OR TRIGGER THE WORKFLOW,<br>THEN SERVE THIS FOLDER: <b>python -m http.server 8080</b></div>`;
  }
}

$("search").addEventListener("input", (e) => { state.search = e.target.value; renderFeed(); });
$("sort").addEventListener("change", (e) => { state.sort = e.target.value; renderFeed(); });
$("refresh").addEventListener("click", refresh);
setInterval(refresh, 300000);
tickClock();
refresh();
