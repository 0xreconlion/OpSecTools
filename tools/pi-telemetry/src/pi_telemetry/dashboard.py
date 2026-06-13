#!/usr/bin/python3
"""Lightweight Raspberry Pi telemetry dashboard.

Reads local system telemetry through psutil plus Pi thermal data from /sys.
Serves one self-contained browser dashboard and a JSON endpoint.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import platform
import socket
import subprocess
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import cast

import psutil


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8788
TEMP_PATHS = (
    Path("/sys/class/thermal/thermal_zone0/temp"),
    Path("/sys/class/hwmon/hwmon0/temp1_input"),
)


HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Pi Telemetry Dashboard</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0b0f14;
      --panel: #121922;
      --panel-2: #17212c;
      --text: #e7eef7;
      --muted: #91a1b4;
      --line: #263545;
      --green: #38d47a;
      --amber: #f4bd4f;
      --red: #ff5d63;
      --blue: #55b7ff;
      --violet: #a88cff;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--text);
      font: 14px/1.4 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    main {
      width: min(1220px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 22px 0 34px;
    }

    header {
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 18px;
      margin-bottom: 18px;
    }

    h1 {
      margin: 0;
      font-size: clamp(26px, 4vw, 44px);
      line-height: 1;
      letter-spacing: 0;
    }

    .subline {
      margin-top: 8px;
      color: var(--muted);
      font-size: 14px;
    }

    .status {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: flex-end;
      gap: 8px;
      color: var(--muted);
      text-align: right;
    }

    .pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 7px 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      color: var(--text);
      white-space: nowrap;
    }

    .dot {
      width: 9px;
      height: 9px;
      border-radius: 50%;
      background: var(--green);
      box-shadow: 0 0 12px currentColor;
    }

    .grid {
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 12px;
    }

    .card {
      grid-column: span 3;
      min-height: 158px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: linear-gradient(180deg, var(--panel), var(--panel-2));
      padding: 14px;
      overflow: hidden;
    }

    .wide { grid-column: span 6; }
    .full { grid-column: span 12; }

    .label {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .08em;
    }

    .value {
      margin-top: 8px;
      font-size: 34px;
      font-weight: 750;
      letter-spacing: 0;
    }

    .unit {
      color: var(--muted);
      font-size: 15px;
      font-weight: 600;
    }

    .meter {
      height: 9px;
      margin-top: 12px;
      border-radius: 999px;
      background: #0a0d12;
      border: 1px solid #1c2936;
      overflow: hidden;
    }

    .fill {
      height: 100%;
      width: 0%;
      background: var(--green);
      transition: width .25s ease, background-color .25s ease;
    }

    .details {
      margin-top: 10px;
      color: var(--muted);
      font-size: 13px;
    }

    .gauge-wrap {
      display: grid;
      grid-template-columns: 116px 1fr;
      align-items: center;
      gap: 14px;
      margin-top: 12px;
    }

    .gauge {
      --value: 0;
      --gauge-color: var(--green);
      width: 112px;
      aspect-ratio: 1;
      border-radius: 50%;
      background:
        radial-gradient(circle at center, var(--panel) 0 54%, transparent 55%),
        conic-gradient(var(--gauge-color) calc(var(--value) * 1%), #0a0d12 0);
      border: 1px solid var(--line);
      display: grid;
      place-items: center;
      color: var(--text);
      font-size: 22px;
      font-weight: 800;
    }

    canvas {
      width: 100%;
      height: 56px;
      display: block;
      margin-top: 12px;
      border-radius: 6px;
      background: #0a0d12;
      border: 1px solid #1c2936;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 10px;
      font-size: 13px;
    }

    th, td {
      border-bottom: 1px solid var(--line);
      padding: 8px 6px;
      text-align: left;
      vertical-align: top;
    }

    th {
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: .08em;
    }

    td:last-child, th:last-child { text-align: right; }

    .muted { color: var(--muted); }
    .ok { color: var(--green); }
    .warn { color: var(--amber); }
    .bad { color: var(--red); }

    @media (max-width: 980px) {
      .card, .wide { grid-column: span 6; }
    }

    @media (max-width: 640px) {
      main { width: min(100vw - 20px, 1220px); padding-top: 14px; }
      header { align-items: flex-start; flex-direction: column; }
      .status { justify-content: flex-start; text-align: left; }
      .card, .wide, .full { grid-column: span 12; }
      .gauge-wrap { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>Pi Telemetry</h1>
        <div class="subline">Live local feed for CPU, thermals, memory, disk, network, and process pressure.</div>
      </div>
      <div class="status">
        <span class="pill"><span class="dot" id="feed-dot"></span><span id="feed-state">connecting</span></span>
        <span class="pill" id="host-pill">host: --</span>
        <span class="pill" id="uptime-pill">uptime: --</span>
      </div>
    </header>

    <section class="grid">
      <article class="card">
        <div class="label"><span>CPU Load</span><span id="cpu-state" class="ok">nominal</span></div>
        <div class="gauge-wrap">
          <div class="gauge" id="cpu-gauge">0%</div>
          <div>
            <div class="value"><span id="cpu-value">0</span><span class="unit">%</span></div>
            <div class="meter"><div class="fill" id="cpu-fill"></div></div>
            <div class="details" id="cpu-detail">per-core: --</div>
          </div>
        </div>
      </article>

      <article class="card">
        <div class="label"><span>Temperature</span><span id="temp-state" class="ok">cool</span></div>
        <div class="gauge-wrap">
          <div class="gauge" id="temp-gauge">0C</div>
          <div>
            <div class="value"><span id="temp-value">0</span><span class="unit">C</span></div>
            <div class="meter"><div class="fill" id="temp-fill"></div></div>
            <div class="details" id="temp-detail">source: --</div>
          </div>
        </div>
      </article>

      <article class="card">
        <div class="label"><span>Memory</span><span id="mem-state" class="ok">clear</span></div>
        <div class="value"><span id="mem-value">0</span><span class="unit">%</span></div>
        <div class="meter"><div class="fill" id="mem-fill"></div></div>
        <div class="details" id="mem-detail">-- used of --</div>
        <canvas id="mem-chart" width="300" height="70"></canvas>
      </article>

      <article class="card">
        <div class="label"><span>Root Disk</span><span id="disk-state" class="ok">room</span></div>
        <div class="value"><span id="disk-value">0</span><span class="unit">%</span></div>
        <div class="meter"><div class="fill" id="disk-fill"></div></div>
        <div class="details" id="disk-detail">-- used of --</div>
        <canvas id="disk-chart" width="300" height="70"></canvas>
      </article>

      <article class="card wide">
        <div class="label"><span>Load Average</span><span id="load-state" class="ok">balanced</span></div>
        <div class="value" id="load-value">--</div>
        <div class="details" id="load-detail">normalized to available cores</div>
        <canvas id="cpu-chart" width="640" height="70"></canvas>
      </article>

      <article class="card wide">
        <div class="label"><span>Network</span><span id="net-state" class="ok">live</span></div>
        <div class="value"><span id="net-down">0 B/s</span> <span class="unit">down</span></div>
        <div class="value" style="font-size: 24px;"><span id="net-up">0 B/s</span> <span class="unit">up</span></div>
        <div class="details" id="net-detail">interfaces: --</div>
        <canvas id="net-chart" width="640" height="70"></canvas>
      </article>

      <article class="card wide">
        <div class="label"><span>Pi Health</span><span id="health-state" class="ok">standing by</span></div>
        <table>
          <tbody id="health-table"></tbody>
        </table>
      </article>

      <article class="card wide">
        <div class="label"><span>Top Processes</span><span class="muted">cpu sorted</span></div>
        <table>
          <thead><tr><th>PID</th><th>Name</th><th>CPU</th><th>MEM</th></tr></thead>
          <tbody id="process-table"></tbody>
        </table>
      </article>
    </section>
  </main>

  <script>
    const history = { cpu: [], temp: [], mem: [], disk: [], net: [] };
    const maxPoints = 80;

    function $(id) { return document.getElementById(id); }

    function clamp(value, min, max) {
      return Math.max(min, Math.min(max, value));
    }

    function escapeHtml(value) {
      return String(value).replace(/[&<>"']/g, ch => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
      }[ch]));
    }

    function bytes(value) {
      if (!Number.isFinite(value)) return '--';
      const units = ['B', 'KB', 'MB', 'GB', 'TB'];
      let size = Math.abs(value);
      let unit = 0;
      while (size >= 1024 && unit < units.length - 1) {
        size /= 1024;
        unit++;
      }
      return `${value < 0 ? '-' : ''}${size.toFixed(size >= 10 || unit === 0 ? 0 : 1)} ${units[unit]}`;
    }

    function colorFor(value, warn = 70, bad = 85) {
      if (value >= bad) return 'var(--red)';
      if (value >= warn) return 'var(--amber)';
      return 'var(--green)';
    }

    function stateClass(value, warn = 70, bad = 85) {
      if (value >= bad) return ['bad', 'hot'];
      if (value >= warn) return ['warn', 'watch'];
      return ['ok', 'nominal'];
    }

    function setMeter(prefix, percent, warn = 70, bad = 85) {
      const value = clamp(Number(percent) || 0, 0, 100);
      const color = colorFor(value, warn, bad);
      const fill = $(`${prefix}-fill`);
      if (fill) {
        fill.style.width = `${value}%`;
        fill.style.backgroundColor = color;
      }
      const gauge = $(`${prefix}-gauge`);
      if (gauge) {
        gauge.style.setProperty('--value', value);
        gauge.style.setProperty('--gauge-color', color);
      }
      const state = $(`${prefix}-state`);
      if (state) {
        const [klass, label] = stateClass(value, warn, bad);
        state.className = klass;
        state.textContent = label;
      }
    }

    function pushHistory(key, value) {
      history[key].push(value);
      if (history[key].length > maxPoints) history[key].shift();
    }

    function drawChart(canvasId, data, color) {
      const canvas = $(canvasId);
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      const h = canvas.height;
      const w = canvas.width;
      const dpr = window.devicePixelRatio || 1;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      ctx.scale(dpr, dpr);
      ctx.fillStyle = '#0a0d12';
      ctx.fillRect(0, 0, w, h);
      if (data.length < 2) return;
      const max = Math.max(...data, 100);
      const xStep = w / (data.length - 1);
      ctx.strokeStyle = color;
      ctx.lineWidth = 3;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.beginPath();
      data.forEach((v, i) => {
        const x = i * xStep;
        const y = h - (v / max) * h;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();
      ctx.fillStyle = color.replace(')', ', 0.1)').replace('rgb', 'rgba');
      ctx.fill();
    }

    function render(data) {
      const cpu = data.cpu.percent;
      const temp = data.temperature.celsius;
      const mem = data.memory.percent;
      const disk = data.disk.percent;
      const load_1 = data.load.normalized_1;

      $('feed-dot').style.background = 'var(--green)';
      $('feed-state').textContent = 'live';
      $('host-pill').textContent = `host: ${escapeHtml(data.host.hostname)}`;
      $('uptime-pill').textContent = `uptime: ${escapeHtml(data.host.uptime)}`;

      setMeter('cpu', cpu);
      setMeter('temp', temp * 1.4, 60, 75);
      setMeter('mem', mem);
      setMeter('disk', disk);

      $('cpu-value').textContent = cpu.toFixed(1);
      $('cpu-detail').textContent = `per-core: ${data.cpu.per_core.map(v => v.toFixed(0)).join(', ')}`;

      $('temp-value').textContent = (temp || 0).toFixed(1);
      $('temp-detail').textContent = `source: ${escapeHtml(data.temperature.source || 'unavailable')}`;

      $('mem-value').textContent = mem.toFixed(1);
      $('mem-detail').textContent = `${bytes(data.memory.used)} used of ${bytes(data.memory.total)}`;

      $('disk-value').textContent = disk.toFixed(1);
      $('disk-detail').textContent = `${bytes(data.disk.used)} used of ${bytes(data.disk.total)}`;

      $('load-value').textContent = load_1.toFixed(2);
      const [loadKlass, loadLabel] = stateClass(load_1 * 100);
      $('load-state').className = loadKlass;
      $('load-state').textContent = loadLabel;

      $('net-down').textContent = bytes(data.network.rx_rate) + '/s';
      $('net-up').textContent = bytes(data.network.tx_rate) + '/s';
      $('net-detail').textContent = `interfaces: ${escapeHtml(data.network.interfaces.join(', ') || 'none')}`;

      $('health-table').innerHTML = `
        <tr><td>Hostname</td><td>${escapeHtml(data.host.hostname)}</td></tr>
        <tr><td>CPU cores</td><td>${data.cpu.count} @ ${data.cpu.frequency_mhz || '?'} MHz</td></tr>
        <tr><td>Memory</td><td>${data.memory.total_gb} GB</td></tr>
        <tr><td>Throttled</td><td>${escapeHtml(data.throttle.status)}</td></tr>
        <tr><td>Boot time</td><td>${escapeHtml(data.host.boot_time)}</td></tr>
        <tr><td>Platform</td><td>${escapeHtml(data.host.platform)}</td></tr>
        <tr><td>Dashboard refresh</td><td>${data.refresh_seconds.toFixed(1)}s</td></tr>
      `;

      $('process-table').innerHTML = data.processes.map(proc => `
        <tr>
          <td>${proc.pid}</td>
          <td>${escapeHtml(proc.name)}</td>
          <td>${proc.cpu_percent.toFixed(1)}%</td>
          <td>${proc.memory_percent.toFixed(1)}%</td>
        </tr>
      `).join('');

      pushHistory('cpu', cpu);
      pushHistory('temp', temp || 0);
      pushHistory('mem', mem);
      pushHistory('disk', disk);
      pushHistory('net', Math.min(100, (data.network.rx_rate + data.network.tx_rate) / (1024 * 1024) * 10));

      drawChart('cpu-chart', history.cpu, '#55b7ff');
      drawChart('mem-chart', history.mem, '#a88cff');
      drawChart('disk-chart', history.disk, '#f4bd4f');
      drawChart('net-chart', history.net, '#38d47a');
    }

    async function tick() {
      try {
        const response = await fetch('/api/telemetry', { cache: 'no-store' });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        render(await response.json());
      } catch (error) {
        $('feed-state').textContent = 'offline';
        $('feed-dot').style.background = 'var(--red)';
      }
    }

    tick();
    setInterval(tick, 1000);
  </script>
</body>
</html>
"""


def bytes_to_gb(value: int) -> float:
    return round(value / 1024 / 1024 / 1024, 2)


def format_duration(seconds: float) -> str:
    seconds = int(seconds)
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    if days:
        return f"{days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def read_temperature() -> tuple[float | None, str | None]:
    for path in TEMP_PATHS:
        try:
            raw = path.read_text(encoding="utf-8").strip()
            value = float(raw)
            if value > 1000:
                value /= 1000
            return round(value, 1), str(path)
        except (OSError, ValueError):
            continue
    temps = psutil.sensors_temperatures(fahrenheit=False)
    for name, entries in temps.items():
        for entry in entries:
            if entry.current is not None:
                return round(float(entry.current), 1), f"psutil:{name}"
    return None, None


class ThrottleCache:
    """Caches vcgencmd result for 10 seconds to avoid subprocess spam."""

    def __init__(self) -> None:
        self.cached_status: str | None = None
        self.cached_time: float = 0
        self.lock = threading.Lock()

    def get_throttle_status(self) -> str:
        now = time.time()
        with self.lock:
            if self.cached_status is not None and (now - self.cached_time) < 10.0:
                return self.cached_status

            try:
                result = subprocess.run(
                    ["vcgencmd", "get_throttled"],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=0.5,
                )
            except (OSError, subprocess.SubprocessError):
                self.cached_status = "unavailable"
                self.cached_time = now
                return self.cached_status

            output = (result.stdout or result.stderr).strip()
            if result.returncode != 0:
                status = output or "unavailable"
            elif "0x0" in output:
                status = f"{output} (clear)"
            else:
                status = output or "unknown"

            self.cached_status = status
            self.cached_time = now
            return status


def process_snapshot() -> list[dict[str, float | int | str]]:
    rows: list[dict[str, float | int | str]] = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            info = proc.info
            rows.append(
                {
                    "pid": int(info["pid"]),
                    "name": str(info.get("name") or "unknown")[:64],
                    "cpu_percent": round(float(info.get("cpu_percent") or 0.0), 1),
                    "memory_percent": round(float(info.get("memory_percent") or 0.0), 1),
                }
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
            continue
    rows.sort(key=lambda item: (item["cpu_percent"], item["memory_percent"]), reverse=True)
    return rows[:8]


def network_snapshot(previous: dict[str, object] | None) -> dict[str, object]:
    counters = psutil.net_io_counters(pernic=True)
    now = time.monotonic()
    interfaces = [
        name
        for name, stats in counters.items()
        if name != "lo" and (stats.bytes_recv or stats.bytes_sent)
    ]
    rx_total = sum(counters[name].bytes_recv for name in interfaces)
    tx_total = sum(counters[name].bytes_sent for name in interfaces)

    rx_rate = 0.0
    tx_rate = 0.0
    if previous:
        previous_time = cast(float, previous["time"])
        previous_rx_total = cast(int, previous["rx_total"])
        previous_tx_total = cast(int, previous["tx_total"])
        elapsed = max(now - previous_time, 0.001)
        rx_rate = max(0.0, (rx_total - previous_rx_total) / elapsed)
        tx_rate = max(0.0, (tx_total - previous_tx_total) / elapsed)

    return {
        "time": now,
        "rx_total": rx_total,
        "tx_total": tx_total,
        "rx_rate": round(rx_rate, 1),
        "tx_rate": round(tx_rate, 1),
        "interfaces": interfaces,
    }


class TelemetryState:
    """Thread-safe telemetry snapshot provider."""

    def __init__(self, throttle_cache: ThrottleCache) -> None:
        self.previous_network: dict[str, object] | None = None
        self.lock = threading.Lock()
        self.throttle_cache = throttle_cache
        # Prime the CPU percent sampler
        for proc in psutil.process_iter():
            try:
                proc.cpu_percent(None)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

    def snapshot(self) -> dict[str, object]:
        with self.lock:
            net = network_snapshot(self.previous_network)
            self.previous_network = net

        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()
        disk = psutil.disk_usage("/")
        temp, temp_source = read_temperature()
        load_1, load_5, load_15 = os.getloadavg()
        cpu_count = psutil.cpu_count() or 1
        cpu_freq = psutil.cpu_freq()
        boot_time = psutil.boot_time()

        return {
            "refresh_seconds": 1.0,
            "host": {
                "hostname": socket.gethostname(),
                "platform": platform.platform(),
                "boot_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(boot_time)),
                "uptime": format_duration(time.time() - boot_time),
            },
            "cpu": {
                "percent": round(psutil.cpu_percent(interval=None), 1),
                "per_core": [
                    round(value, 1) for value in psutil.cpu_percent(interval=None, percpu=True)
                ],
                "count": cpu_count,
                "frequency_mhz": round(cpu_freq.current) if cpu_freq else None,
            },
            "load": {
                "avg_1": load_1,
                "avg_5": load_5,
                "avg_15": load_15,
                "normalized_1": load_1 / cpu_count,
            },
            "memory": {
                "total": vm.total,
                "used": vm.used,
                "available": vm.available,
                "percent": round(vm.percent, 1),
                "total_gb": bytes_to_gb(vm.total),
                "available_gb": bytes_to_gb(vm.available),
            },
            "swap": {
                "total": swap.total,
                "used": swap.used,
                "percent": round(swap.percent, 1),
            },
            "disk": {
                "path": "/",
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": round(disk.percent, 1),
            },
            "temperature": {
                "celsius": temp,
                "source": temp_source,
            },
            "network": {
                "rx_rate": net["rx_rate"],
                "tx_rate": net["tx_rate"],
                "rx_total": net["rx_total"],
                "tx_total": net["tx_total"],
                "interfaces": net["interfaces"],
            },
            "processes": process_snapshot(),
            "throttle": {
                "status": self.throttle_cache.get_throttle_status(),
            },
            "glances": {
                "server_running": any(
                    "glances" in " ".join(proc.info.get("cmdline") or []).lower()
                    for proc in psutil.process_iter(["cmdline"])
                    if proc.info.get("cmdline")
                )
            },
        }


class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP request handler for telemetry endpoints."""

    # Set by main() via functools.partial
    state: TelemetryState = None  # type: ignore

    def log_message(self, fmt: str, *args: object) -> None:
        """Suppress default request logging."""
        return

    def send_json(self, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_html(self) -> None:
        body = HTML.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "default-src 'self'")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path in {"/", "/index.html"}:
            self.send_html()
            return
        if self.path == "/api/telemetry":
            self.send_json(self.state.snapshot())
            return
        if self.path == "/health":
            self.send_json({"ok": True})
            return

        escaped_path = html.escape(self.path)
        body = f"Not found: {escaped_path}\n".encode("utf-8")
        self.send_response(HTTPStatus.NOT_FOUND)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve a lightweight Pi telemetry dashboard.")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Bind address")
    parser.add_argument("--port", default=DEFAULT_PORT, type=int, help="Bind port")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    throttle_cache = ThrottleCache()
    state = TelemetryState(throttle_cache)

    # Create a handler class that captures the state instance
    def make_handler_class(state_instance: TelemetryState):
        class ClosureHandler(DashboardHandler):
            state = state_instance

        return ClosureHandler

    handler_class = make_handler_class(state)
    server = ThreadingHTTPServer((args.host, args.port), handler_class)
    print(f"Pi telemetry dashboard available at http://{args.host}:{args.port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
