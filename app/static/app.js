const API = "/api";
let selectedMonitor = null;
let monitors = [];
let chart = null;

const $ = (id) => document.getElementById(id);

function fmtMs(value) {
  return value === null || value === undefined ? "-" : `${Math.round(value)}ms`;
}

function fmtUptime(value) {
  return value === null || value === undefined ? "-" : `${Number(value).toFixed(1)}%`;
}

function fmtDate(value) {
  if (!value) return "-";
  return new Date(value).toLocaleString("pl-PL");
}

function statusClass(status) {
  if (status === "up") return "up";
  if (status === "down") return "down";
  if (status === "partial") return "partial";
  return "unknown";
}

async function api(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok && res.status !== 204) {
    const msg = await res.text();
    throw new Error(msg || `HTTP ${res.status}`);
  }
  return res.status === 204 ? null : res.json();
}

async function loadMonitors() {
  monitors = await api("/monitors/");
  renderTargets();

  if (!selectedMonitor && monitors.length) {
    selectedMonitor = monitors[0];
  }
  if (selectedMonitor) {
    const fresh = monitors.find(m => m.id === selectedMonitor.id);
    selectedMonitor = fresh || monitors[0] || null;
  }
  await loadSelected();
}

function renderTargets() {
  const box = $("targets");
  box.innerHTML = "";

  if (!monitors.length) {
    box.innerHTML = `<div class="empty">Brak monitorów</div>`;
    return;
  }

  monitors.forEach((monitor) => {
    const item = document.createElement("div");
    item.className = `target-item ${selectedMonitor?.id === monitor.id ? "active" : ""}`;
    item.innerHTML = `
      <span class="target-url" title="${monitor.url}">${monitor.url}</span>
      <button class="delete-btn" title="Usuń">×</button>
    `;
    item.addEventListener("click", () => {
      selectedMonitor = monitor;
      renderTargets();
      loadSelected();
    });
    item.querySelector("button").addEventListener("click", async (e) => {
      e.stopPropagation();
      await api(`/monitors/${monitor.id}`, { method: "DELETE" });
      if (selectedMonitor?.id === monitor.id) selectedMonitor = null;
      await loadMonitors();
    });
    box.appendChild(item);
  });
}

async function loadSelected() {
  if (!selectedMonitor) {
    $("selectedUrl").textContent = "Dodaj pierwszy monitor";
    $("statusText").textContent = "unknown";
    $("recentPing").textContent = "-";
    $("avgPing").textContent = "-";
    $("recentResponse").textContent = "-";
    $("uptime24").textContent = "-";
    $("historyRows").innerHTML = `<tr><td colspan="5">Brak danych</td></tr>`;
    updateDot(null);
    updateChart([]);
    return;
  }

  $("selectedUrl").textContent = selectedMonitor.url;

  const [stats, checks, chartData] = await Promise.all([
    api(`/monitors/${selectedMonitor.id}/stats?period=24h`),
    api(`/monitors/${selectedMonitor.id}/checks?limit=50&offset=0`),
    api(`/monitors/${selectedMonitor.id}/stats/uptime-chart?period=24h&bucket=1h`),
  ]);

  const recent = checks.items?.[0];
  $("statusText").textContent = stats.current_status || recent?.combined_status || "unknown";
  $("recentPing").textContent = fmtMs(recent?.ping_ms);
  $("avgPing").textContent = fmtMs(stats.ping_avg_response_time_ms);
  $("recentResponse").textContent = recent?.http_response || "-";
  $("uptime24").textContent = fmtUptime(stats.uptime_percentage);
  updateDot(stats.current_status || recent?.combined_status);
  renderHistory(checks.items || []);
  updateChart(chartData.buckets || []);
}

function updateDot(status) {
  $("liveDot").className = `status-dot ${statusClass(status)}`;
}

function renderHistory(items) {
  const tbody = $("historyRows");
  if (!items.length) {
    tbody.innerHTML = `<tr><td colspan="5">Brak sprawdzeń</td></tr>`;
    return;
  }
  tbody.innerHTML = items.map(row => `
    <tr>
      <td>${selectedMonitor.url}</td>
      <td>${fmtMs(row.ping_ms)}</td>
      <td>${row.http_response || "-"}</td>
      <td><span class="status-pill ${statusClass(row.combined_status)}"></span></td>
      <td>${fmtDate(row.checked_at)}</td>
    </tr>
  `).join("");
}

function updateChart(buckets) {
  const ctx = $("uptimeChart");
  const labels = buckets.map(b => new Date(b.time_start).toLocaleTimeString("pl-PL", { hour: "2-digit", minute: "2-digit" }));
  const data = buckets.map(b => Number(b.uptime_percentage));

  if (chart) chart.destroy();
  chart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [{
        label: "Uptime %",
        data,
        tension: 0.35,
        fill: false,
        pointRadius: 2,
        borderWidth: 2,
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: { min: 0, max: 100, ticks: { color: "#d8d9e8" }, grid: { color: "rgba(255,255,255,.12)" } },
        x: { ticks: { color: "#d8d9e8", maxTicksLimit: 8 }, grid: { color: "rgba(255,255,255,.08)" } }
      }
    }
  });
}

$("addMonitorForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = $("monitorUrl");
  await api("/monitors/", {
    method: "POST",
    body: JSON.stringify({ url: input.value.trim() }),
  });
  input.value = "";
  await loadMonitors();
});

loadMonitors().catch(err => alert(`Błąd ładowania: ${err.message}`));
setInterval(() => loadMonitors().catch(console.error), 15000);
