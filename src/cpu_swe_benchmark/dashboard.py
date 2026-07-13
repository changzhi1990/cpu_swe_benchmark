from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

from cpu_swe_benchmark.business_metrics import load_business_summary
from cpu_swe_benchmark.system_history import SystemHistory
from cpu_swe_benchmark.system_metrics import read_system_metrics

app = FastAPI(title="CPU SWE Benchmark Dashboard")
system_history = SystemHistory(max_points=120)


HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>CPU SWE Benchmark Dashboard</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --ink: #1f2933;
      --muted: #667085;
      --line: #d8dee8;
      --accent: #136f63;
      --warn: #a15c07;
      --bad: #a61b1b;
    }
    body {
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--ink);
    }
    header {
      padding: 18px 24px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
    }
    h1 { font-size: 20px; margin: 0; }
    h2 { font-size: 15px; margin: 0 0 12px; }
    main { padding: 20px 24px 32px; }
    .grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }
    .wide { grid-column: 1 / -1; }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      min-width: 0;
    }
    .metric { font-size: 26px; font-weight: 700; }
    .label { color: var(--muted); font-size: 12px; margin-top: 2px; }
    .ok { color: var(--accent); }
    .warn { color: var(--warn); }
    .bad { color: var(--bad); }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { padding: 8px 9px; border-bottom: 1px solid var(--line); text-align: right; white-space: nowrap; }
    th:first-child, td:first-child { text-align: left; }
    th { color: var(--muted); font-weight: 600; background: #fbfcfe; }
    .gpu-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
    .gpu { border: 1px solid var(--line); border-radius: 6px; padding: 10px; }
    .chart-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; margin-bottom: 18px; }
    .chart-card { border: 1px solid var(--line); border-radius: 8px; padding: 12px; min-width: 0; }
    .chart-title { display: flex; justify-content: space-between; gap: 10px; align-items: baseline; margin-bottom: 8px; }
    .chart-title strong { font-size: 14px; }
    .chart-title span { color: var(--muted); font-size: 12px; }
    .chart { width: 100%; height: 220px; display: block; background: #fbfcfe; border: 1px solid #edf0f5; border-radius: 6px; }
    .legend { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 8px; }
    .legend-item { font-size: 12px; color: var(--muted); display: inline-flex; gap: 5px; align-items: center; }
    .swatch { width: 10px; height: 10px; border-radius: 2px; display: inline-block; }
    .bar { height: 7px; background: #e6eaf0; border-radius: 999px; overflow: hidden; margin-top: 8px; }
    .fill { height: 100%; background: var(--accent); width: 0%; }
    select { padding: 6px 8px; border: 1px solid var(--line); border-radius: 6px; background: #fff; }
    @media (max-width: 1100px) { .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } .gpu-grid, .chart-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
    @media (max-width: 780px) { .grid, .gpu-grid, .chart-grid { grid-template-columns: 1fr; } header { align-items: flex-start; flex-direction: column; } }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>CPU SWE Benchmark Dashboard</h1>
      <div class="label">System and benchmark metrics. Auto-refreshes every 5 seconds.</div>
    </div>
    <div>
      <label class="label" for="runSelect">Run</label>
      <select id="runSelect"></select>
    </div>
  </header>
  <main>
    <section class="grid">
      <div class="panel"><h2>CPU</h2><div id="cpu" class="metric">--%</div><div class="label">utilization</div></div>
      <div class="panel"><h2>Load</h2><div id="load" class="metric">--</div><div class="label">1m / 5m / 15m</div></div>
      <div class="panel"><h2>Memory</h2><div id="memory" class="metric">--%</div><div class="label" id="memoryText">used</div></div>
      <div class="panel"><h2>vLLM</h2><div id="container" class="metric">--</div><div class="label">container status</div></div>
      <div class="panel wide"><h2>System Utilization History</h2><div id="systemCharts" class="chart-grid"></div></div>
      <div class="panel wide"><h2>GPU</h2><div id="gpus" class="gpu-grid"></div></div>
      <div class="panel wide">
        <h2>Business Metrics</h2>
        <div id="businessCharts" class="chart-grid"></div>
        <table>
          <thead>
            <tr>
              <th>workload</th><th>conc.</th><th>success</th><th>throughput/s</th><th>p50 s</th><th>p90 s</th><th>p99 s</th><th>LLM s</th><th>bash s</th>
            </tr>
          </thead>
          <tbody id="businessRows"></tbody>
        </table>
      </div>
    </section>
  </main>
  <script>
    const runSelect = document.getElementById('runSelect');
    let selectedRun = null;

    function fmt(value, digits = 2) {
      if (value === null || value === undefined || value === '') return '--';
      const n = Number(value);
      return Number.isFinite(n) ? n.toFixed(digits) : String(value);
    }

    const palette = ['#136f63', '#4f46e5', '#c2410c', '#be123c', '#0f766e', '#7c3aed'];

    function drawChart(group) {
      const width = 560, height = 220, padL = 48, padR = 16, padT = 18, padB = 34;
      const allPoints = group.series.flatMap(s => s.points);
      if (!allPoints.length) return '';
      const xs = allPoints.map(p => Number(p.x));
      const ys = allPoints.map(p => Number(p.y));
      const minX = Math.min(...xs), maxX = Math.max(...xs);
      const minY = Math.min(0, Math.min(...ys));
      const maxY = Math.max(...ys);
      const ySpan = maxY - minY || 1;
      const xSpan = maxX - minX || 1;
      const xScale = x => padL + ((x - minX) / xSpan) * (width - padL - padR);
      const yScale = y => height - padB - ((y - minY) / ySpan) * (height - padT - padB);
      const yTicks = [minY, minY + ySpan / 2, maxY];
      const xTicks = [...new Set(xs)].sort((a, b) => a - b);
      const paths = group.series.map((series, idx) => {
        const color = palette[idx % palette.length];
        const d = series.points.map((p, i) => `${i ? 'L' : 'M'} ${xScale(Number(p.x)).toFixed(1)} ${yScale(Number(p.y)).toFixed(1)}`).join(' ');
        const dots = series.points.map(p => `<circle cx="${xScale(Number(p.x)).toFixed(1)}" cy="${yScale(Number(p.y)).toFixed(1)}" r="3" fill="${color}"><title>${series.label}: ${fmt(p.y, 3)} @ ${p.x}</title></circle>`).join('');
        return `<path d="${d}" fill="none" stroke="${color}" stroke-width="2.2" />${dots}`;
      }).join('');
      const xLabels = xTicks.map(x => `<text x="${xScale(x).toFixed(1)}" y="${height - 10}" text-anchor="middle" font-size="10" fill="#667085">${x}</text>`).join('');
      const yLabels = yTicks.map(y => `<g><line x1="${padL}" x2="${width - padR}" y1="${yScale(y).toFixed(1)}" y2="${yScale(y).toFixed(1)}" stroke="#edf0f5"/><text x="${padL - 7}" y="${(yScale(y)+3).toFixed(1)}" text-anchor="end" font-size="10" fill="#667085">${fmt(y, 2)}</text></g>`).join('');
      const legend = group.series.map((series, idx) => `<span class="legend-item"><span class="swatch" style="background:${palette[idx % palette.length]}"></span>${series.label}</span>`).join('');
      return `<div class="chart-card">
        <div class="chart-title"><strong>${group.title}</strong><span>${group.unit}</span></div>
        <svg class="chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="${group.title}">
          ${yLabels}
          <line x1="${padL}" x2="${width - padR}" y1="${height - padB}" y2="${height - padB}" stroke="#d8dee8"/>
          <line x1="${padL}" x2="${padL}" y1="${padT}" y2="${height - padB}" stroke="#d8dee8"/>
          ${xLabels}
          <text x="${width / 2}" y="${height - 2}" text-anchor="middle" font-size="10" fill="#667085">concurrency</text>
          ${paths}
        </svg>
        <div class="legend">${legend}</div>
      </div>`;
    }

    async function refreshSystem() {
      const data = await fetch('/api/system').then(r => r.json());
      document.getElementById('cpu').textContent = fmt(data.cpu.utilization_percent, 1) + '%';
      document.getElementById('load').textContent = `${fmt(data.load.load_1m)} / ${fmt(data.load.load_5m)} / ${fmt(data.load.load_15m)}`;
      document.getElementById('memory').textContent = fmt(data.memory.used_percent, 1) + '%';
      document.getElementById('memoryText').textContent = `${fmt(data.memory.used_bytes / 1073741824, 1)} / ${fmt(data.memory.total_bytes / 1073741824, 1)} GiB`;
      const container = document.getElementById('container');
      container.textContent = data.vllm_container.status || 'unknown';
      container.className = 'metric ' + (data.vllm_container.status === 'running' ? 'ok' : 'warn');
      const gpus = document.getElementById('gpus');
      gpus.innerHTML = '';
      for (const gpu of data.gpus) {
        const div = document.createElement('div');
        div.className = 'gpu';
        if (gpu.error) {
          div.textContent = gpu.error;
        } else {
          div.innerHTML = `<strong>GPU ${gpu.index}</strong><div class="label">${gpu.name}</div>
            <div>util ${fmt(gpu.utilization_gpu_percent, 0)}%</div>
            <div>mem ${fmt(gpu.memory_used_mib, 0)} / ${fmt(gpu.memory_total_mib, 0)} MiB</div>
            <div class="bar"><div class="fill" style="width:${gpu.memory_used_percent}%"></div></div>`;
        }
        gpus.appendChild(div);
      }
      const history = await fetch('/api/system/history').then(r => r.json());
      renderSystemCharts(history);
    }

    function renderSystemCharts(history) {
      const charts = [];
      charts.push(drawChart({
        title: 'CPU Utilization',
        unit: 'percent',
        series: [{ key: 'cpu_utilization', label: 'CPU', points: (history.cpu || []).map((p, idx) => ({ x: idx + 1, y: p.y })) }]
      }));
      charts.push(drawChart({
        title: 'GPU Utilization',
        unit: 'percent',
        series: (history.gpus || []).map(gpu => ({
          key: 'gpu_' + gpu.index,
          label: gpu.label,
          points: (gpu.points || []).map((p, idx) => ({ x: idx + 1, y: p.y }))
        }))
      }));
      document.getElementById('systemCharts').innerHTML = charts.join('');
    }

    async function refreshBusiness() {
      const qs = selectedRun ? '?run=' + encodeURIComponent(selectedRun) : '';
      const data = await fetch('/api/business' + qs).then(r => r.json());
      runSelect.innerHTML = '';
      for (const run of data.runs) {
        const opt = document.createElement('option');
        opt.value = run.path;
        opt.textContent = run.name;
        if (data.selected_run && run.path === data.selected_run.path) opt.selected = true;
        runSelect.appendChild(opt);
      }
      const tbody = document.getElementById('businessRows');
      tbody.innerHTML = '';
      document.getElementById('businessCharts').innerHTML = (data.metric_groups || []).map(drawChart).join('');
      for (const row of data.rows) {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${row.workload}</td><td>${row.concurrency}</td><td>${fmt(row.success_rate, 3)}</td>
          <td>${fmt(row.throughput_successful_tasks_per_sec, 3)}</td><td>${fmt(row.latency_p50)}</td>
          <td>${fmt(row.latency_p90)}</td><td>${fmt(row.latency_p99)}</td>
          <td>${fmt(row.avg_llm_time_seconds_per_task)}</td><td>${fmt(row.avg_bash_time_seconds_per_task)}</td>`;
        tbody.appendChild(tr);
      }
    }

    runSelect.addEventListener('change', () => { selectedRun = runSelect.value; refreshBusiness(); });
    async function tick() {
      try { await refreshSystem(); await refreshBusiness(); } catch (err) { console.error(err); }
    }
    tick();
    setInterval(tick, 5000);
  </script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return HTML


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/system")
def system() -> dict:
    metrics = read_system_metrics()
    system_history.add_sample(metrics)
    return metrics


@app.get("/api/system/history")
def system_history_route() -> dict:
    return system_history.to_payload()


@app.get("/api/business")
def business(run: str | None = Query(default=None)) -> dict:
    return load_business_summary(Path("results"), run)
