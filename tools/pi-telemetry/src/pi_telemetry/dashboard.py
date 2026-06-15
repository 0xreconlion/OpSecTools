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
import secrets
import shutil
import sqlite3
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
CODEX_STATE_PATH = Path.home() / ".codex" / "state_5.sqlite"
DEFAULT_CODEX_PROCESS_MARKER = "codex"
CODEX_THREAD_LIMIT = 8
CODEX_MODEL_LIMIT = 6
CODEX_PROCESS_LIMIT = 8


HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Pi Telemetry Dashboard</title>
  <style nonce="__CSP_NONCE__">
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

    html {
      min-height: 100%;
    }

    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--text);
      font: 14px/1.4 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      overflow-x: hidden;
    }

    main {
      container-type: inline-size;
      width: min(1220px, calc(100vw - clamp(20px, 4vw, 32px)));
      margin: 0 auto;
      padding: clamp(12px, 2.2vh, 22px) 0 clamp(16px, 3vh, 34px);
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

    .header-actions {
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 10px;
    }

    .view-switch {
      display: inline-flex;
      gap: 3px;
      padding: 3px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #0a0d12;
    }

    .view-button {
      min-width: 76px;
      border: 0;
      border-radius: 6px;
      padding: 7px 11px;
      background: transparent;
      color: var(--muted);
      font: inherit;
      cursor: pointer;
    }

    .view-button.active {
      background: var(--panel-2);
      color: var(--text);
    }

    .view-button:focus-visible {
      outline: 2px solid var(--blue);
      outline-offset: 2px;
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
      grid-template-columns: repeat(auto-fit, minmax(min(100%, 260px), 1fr));
      gap: 12px;
      align-items: stretch;
    }

    .view-panel[hidden] {
      display: none;
    }

    .card {
      min-height: clamp(132px, 23vh, 158px);
      border: 1px solid var(--line);
      border-radius: 8px;
      background: linear-gradient(180deg, var(--panel), var(--panel-2));
      padding: clamp(10px, 1.6vw, 14px);
      overflow: hidden;
    }

    .wide { grid-column: span 2; }
    .full { grid-column: 1 / -1; }

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
      font-size: clamp(26px, 3.8vw, 34px);
      font-weight: 750;
      letter-spacing: 0;
    }

    .value.secondary {
      font-size: 24px;
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

    .summary-row {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
      margin-top: 12px;
    }

    .summary-item {
      min-width: 0;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 9px;
      background: #0a0d12;
    }

    .summary-item span {
      display: block;
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: .08em;
    }

    .summary-item strong {
      display: block;
      margin-top: 4px;
      overflow-wrap: anywhere;
      font-size: 18px;
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
      width: clamp(88px, 14vw, 112px);
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
      height: clamp(44px, 8vh, 64px);
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

    @container (max-width: 680px) {
      .wide, .full { grid-column: span 1; }
      .gauge-wrap { grid-template-columns: 1fr; }
      .summary-row { grid-template-columns: 1fr; }
    }

    @media (max-width: 640px) {
      main { width: min(100vw - 20px, 1220px); padding-top: 14px; }
      header { align-items: flex-start; flex-direction: column; }
      .status { justify-content: flex-start; text-align: left; }
      .header-actions { align-items: flex-start; }
      .gauge-wrap { grid-template-columns: 1fr; }
    }

    @media (max-height: 680px) {
      header { margin-bottom: 12px; }
      h1 { font-size: 28px; }
      .subline { display: none; }
      .card { min-height: 118px; }
      table { font-size: 12px; }
      th, td { padding: 6px; }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>Pi Telemetry</h1>
        <div class="subline">Live local feed for host telemetry and metadata-only local LLM pressure.</div>
      </div>
      <div class="header-actions">
        <div class="status">
          <span class="pill"><span class="dot" id="feed-dot"></span><span id="feed-state">connecting</span></span>
          <span class="pill" id="host-pill">host: --</span>
          <span class="pill" id="uptime-pill">uptime: --</span>
        </div>
        <div class="view-switch" role="tablist" aria-label="Telemetry view">
          <button class="view-button active" type="button" role="tab" aria-selected="true" data-view="host">Host</button>
          <button class="view-button" type="button" role="tab" aria-selected="false" data-view="llm">LLM</button>
        </div>
      </div>
    </header>

    <section class="grid view-panel" id="host-view" data-panel="host">
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
        <div class="value secondary"><span id="net-up">0 B/s</span> <span class="unit">up</span></div>
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

    <section class="grid view-panel" id="llm-view" data-panel="llm" hidden>
      <article class="card">
        <div class="label"><span>LLM Pressure</span><span id="llm-pressure-state" class="muted">metadata</span></div>
        <div class="value" id="llm-pressure">--</div>
        <div class="details" id="llm-source">source: codex-cli</div>
        <div class="summary-row">
          <div class="summary-item"><span>Threads</span><strong id="llm-thread-count">--</strong></div>
          <div class="summary-item"><span>CLI</span><strong id="llm-cli-version">--</strong></div>
          <div class="summary-item"><span>Privacy</span><strong id="llm-privacy">metadata</strong></div>
        </div>
      </article>

      <article class="card">
        <div class="label"><span>Token Count</span><span class="muted">codex state</span></div>
        <div class="value" id="llm-total-tokens">--</div>
        <div class="details" id="llm-token-detail">delta: --</div>
      </article>

      <article class="card">
        <div class="label"><span>Token Rate</span><span class="muted">since last poll</span></div>
        <div class="value"><span id="llm-token-rate">--</span><span class="unit">/min</span></div>
        <div class="details" id="llm-activity-detail">latest activity: --</div>
      </article>

      <article class="card">
        <div class="label"><span>Host Pressure</span><span id="llm-host-state" class="ok">nominal</span></div>
        <div class="value"><span id="llm-host-cpu">--</span><span class="unit">% cpu</span></div>
        <div class="details" id="llm-host-detail">memory: -- / temp: --</div>
      </article>

      <article class="card wide">
        <div class="label"><span>Model Mix</span><span id="llm-dominant-model" class="muted">dominant: --</span></div>
        <table>
          <thead><tr><th>Model</th><th>Threads</th><th>Tokens</th></tr></thead>
          <tbody id="llm-model-table"></tbody>
        </table>
      </article>

      <article class="card wide">
        <div class="label"><span>Codex Processes</span><span id="llm-process-count" class="muted">0 detected</span></div>
        <div class="summary-row">
          <div class="summary-item"><span>CPU</span><strong id="llm-process-cpu">--</strong></div>
          <div class="summary-item"><span>Memory</span><strong id="llm-process-mem">--</strong></div>
          <div class="summary-item"><span>RSS</span><strong id="llm-process-rss">--</strong></div>
        </div>
        <table>
          <thead><tr><th>PID</th><th>Name</th><th>CPU</th><th>RSS</th></tr></thead>
          <tbody id="llm-process-table"></tbody>
        </table>
      </article>

      <article class="card full">
        <div class="label"><span>Recent Codex Threads</span><span class="muted">safe metadata</span></div>
        <table>
          <thead><tr><th>Thread</th><th>Model</th><th>Workspace</th><th>Tokens</th><th>Age</th></tr></thead>
          <tbody id="llm-thread-table"></tbody>
        </table>
      </article>

      <article class="card full">
        <div class="label"><span>LLM Telemetry Notes</span><span class="muted">local only</span></div>
        <table>
          <tbody id="llm-warning-list"></tbody>
        </table>
      </article>
    </section>
  </main>

  <script nonce="__CSP_NONCE__">
    const history = { cpu: [], temp: [], mem: [], disk: [], net: [] };
    const POLL_MS = 1000;
    const RESIZE_SETTLE_MS = 650;
    const MAX_DEVICE_PIXEL_RATIO = 2;
    let maxPoints = 80;
    let pollTimer = null;
    let resizeTimer = null;
    let resizeFrame = null;
    let activeController = null;
    let feedState = 'connecting';
    let isResizing = false;
    let inFlight = false;
    let activeView = 'host';

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

    function tokens(value) {
      const numeric = Number(value);
      if (!Number.isFinite(numeric)) return '--';
      const units = ['', 'K', 'M', 'B'];
      let size = Math.abs(numeric);
      let unit = 0;
      while (size >= 1000 && unit < units.length - 1) {
        size /= 1000;
        unit++;
      }
      return `${numeric < 0 ? '-' : ''}${size.toFixed(size >= 10 || unit === 0 ? 0 : 1)}${units[unit]}`;
    }

    function age(seconds) {
      const numeric = Number(seconds);
      if (!Number.isFinite(numeric)) return '--';
      if (numeric < 60) return 'now';
      if (numeric < 3600) return `${Math.floor(numeric / 60)}m`;
      if (numeric < 86400) return `${Math.floor(numeric / 3600)}h`;
      return `${Math.floor(numeric / 86400)}d`;
    }

    function emptyRow(message, columns) {
      return `<tr><td colspan="${columns}" class="muted">${escapeHtml(message)}</td></tr>`;
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

    function pressureClass(pressure) {
      if (pressure === 'heavy') return 'bad';
      if (pressure === 'active') return 'warn';
      if (pressure === 'idle') return 'ok';
      return 'muted';
    }

    function setActiveView(view) {
      activeView = view === 'llm' ? 'llm' : 'host';
      document.querySelectorAll('[data-panel]').forEach(panel => {
        panel.hidden = panel.dataset.panel !== activeView;
      });
      document.querySelectorAll('.view-button').forEach(button => {
        const selected = button.dataset.view === activeView;
        button.classList.toggle('active', selected);
        button.setAttribute('aria-selected', selected ? 'true' : 'false');
        button.tabIndex = selected ? 0 : -1;
      });
      window.requestAnimationFrame(redrawCharts);
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

    function trimHistory() {
      Object.values(history).forEach(points => {
        while (points.length > maxPoints) points.shift();
      });
    }

    function computeMaxPoints() {
      if (window.innerWidth <= 640) return 36;
      if (window.innerWidth <= 980 || window.innerHeight <= 680) return 56;
      return 80;
    }

    function applyLayoutProfile() {
      maxPoints = computeMaxPoints();
      trimHistory();
      document.documentElement.dataset.dashboardProfile =
        window.innerWidth <= 640 ? 'narrow' :
        window.innerHeight <= 680 ? 'short' :
        window.innerWidth <= 980 ? 'snapped' : 'full';
    }

    function setFeedState(state) {
      feedState = state;
      $('feed-state').textContent = state;
      $('feed-dot').style.background =
        state === 'live' ? 'var(--green)' :
        state === 'offline' ? 'var(--red)' :
        state === 'resizing' || state === 'paused' ? 'var(--amber)' : 'var(--blue)';
    }

    function prepareCanvas(canvas) {
      const rect = canvas.getBoundingClientRect();
      const cssWidth = Math.max(1, Math.round(rect.width));
      const cssHeight = Math.max(1, Math.round(rect.height));
      const dpr = Math.min(window.devicePixelRatio || 1, MAX_DEVICE_PIXEL_RATIO);
      const pixelWidth = Math.max(1, Math.round(cssWidth * dpr));
      const pixelHeight = Math.max(1, Math.round(cssHeight * dpr));
      if (canvas.width !== pixelWidth || canvas.height !== pixelHeight) {
        canvas.width = pixelWidth;
        canvas.height = pixelHeight;
      }
      const ctx = canvas.getContext('2d');
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      return { ctx, width: cssWidth, height: cssHeight };
    }

    function drawChart(canvasId, data, color) {
      const canvas = $(canvasId);
      if (!canvas) return;
      const { ctx, width: w, height: h } = prepareCanvas(canvas);
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
    }

    function redrawCharts() {
      drawChart('cpu-chart', history.cpu, '#55b7ff');
      drawChart('mem-chart', history.mem, '#a88cff');
      drawChart('disk-chart', history.disk, '#f4bd4f');
      drawChart('net-chart', history.net, '#38d47a');
    }

    function renderHost(data) {
      const cpu = data.cpu.percent;
      const temp = data.temperature.celsius;
      const mem = data.memory.percent;
      const disk = data.disk.percent;
      const load_1 = data.load.normalized_1;

      setFeedState('live');
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

      redrawCharts();
    }

    function renderLlm(llm, data) {
      const available = Boolean(llm && llm.available);
      const summary = llm && llm.summary ? llm.summary : {};
      const processes = llm && llm.processes ? llm.processes : { count: 0, top: [] };
      const processRows = Array.isArray(processes.top) ? processes.top : [];
      const modelRows = Array.isArray(llm && llm.models) ? llm.models : [];
      const threadRows = Array.isArray(llm && llm.recent_threads) ? llm.recent_threads : [];
      const pressure = String(summary.pressure || (available ? 'idle' : 'unavailable'));
      const pressureState = $('llm-pressure-state');

      $('llm-pressure').textContent = pressure;
      pressureState.className = pressureClass(pressure);
      pressureState.textContent = available ? String(llm.privacy || 'metadata-only') : 'unavailable';
      $('llm-source').textContent = `source: ${llm && llm.source ? llm.source : 'codex-cli'}`;
      $('llm-thread-count').textContent = String(summary.thread_count ?? 0);
      $('llm-cli-version').textContent = summary.cli_version || '--';
      $('llm-privacy').textContent = available ? String(llm.privacy || 'metadata') : 'metadata';

      $('llm-total-tokens').textContent = tokens(summary.total_tokens);
      $('llm-token-detail').textContent = `delta: ${tokens(summary.token_delta || 0)} since last poll`;
      $('llm-token-rate').textContent = tokens(summary.tokens_per_minute || 0);
      $('llm-activity-detail').textContent = `latest activity: ${age(summary.latest_activity_age_seconds)}`;

      const hostCpu = Number(data.cpu.percent) || 0;
      const hostMem = Number(data.memory.percent) || 0;
      const hostTemp = Number(data.temperature.celsius) || 0;
      const hostLoad = Number(data.load.normalized_1) * 100 || 0;
      const hostPressure = Math.max(hostCpu, hostMem, hostTemp * 1.4, hostLoad);
      const [hostKlass, hostLabel] = stateClass(hostPressure);
      $('llm-host-state').className = hostKlass;
      $('llm-host-state').textContent = hostLabel;
      $('llm-host-cpu').textContent = hostCpu.toFixed(1);
      $('llm-host-detail').textContent =
        `memory: ${hostMem.toFixed(1)}% / temp: ${hostTemp ? hostTemp.toFixed(1) + 'C' : '--'}`;

      $('llm-dominant-model').textContent = `dominant: ${summary.dominant_model || '--'}`;
      $('llm-model-table').innerHTML = modelRows.length ? modelRows.map(model => `
        <tr>
          <td>${escapeHtml(model.display || model.model || 'unknown')}</td>
          <td>${Number(model.thread_count || 0)}</td>
          <td>${tokens(model.tokens_used)}</td>
        </tr>
      `).join('') : emptyRow('No Codex model metadata available.', 3);

      $('llm-process-count').textContent = `${Number(processes.count || 0)} detected`;
      $('llm-process-cpu').textContent = `${Number(processes.cpu_percent || 0).toFixed(1)}%`;
      $('llm-process-mem').textContent = `${Number(processes.memory_percent || 0).toFixed(1)}%`;
      $('llm-process-rss').textContent = bytes(Number(processes.memory_bytes || 0));
      $('llm-process-table').innerHTML = processRows.length ? processRows.map(proc => `
        <tr>
          <td>${Number(proc.pid || 0)}</td>
          <td>${escapeHtml(proc.name || 'unknown')}</td>
          <td>${Number(proc.cpu_percent || 0).toFixed(1)}%</td>
          <td>${bytes(Number(proc.memory_bytes || 0))}</td>
        </tr>
      `).join('') : emptyRow('No Codex processes detected.', 4);

      $('llm-thread-table').innerHTML = threadRows.length ? threadRows.map(thread => `
        <tr>
          <td>${escapeHtml(thread.thread_id || 'unknown')}</td>
          <td>${escapeHtml(thread.model || 'unknown')}</td>
          <td>${escapeHtml(thread.cwd || 'unknown')}</td>
          <td>${tokens(thread.tokens_used)}</td>
          <td>${age(thread.age_seconds)}</td>
        </tr>
      `).join('') : emptyRow('No recent Codex thread metadata available.', 5);

      const warnings = ['Prompt and session content are not read.'].concat(
        Array.isArray(llm && llm.warnings) ? llm.warnings : []
      );
      $('llm-warning-list').innerHTML = warnings.map(warning => `
        <tr><td>${escapeHtml(warning)}</td></tr>
      `).join('');
    }

    function render(data) {
      renderHost(data);
      renderLlm(data.llm, data);
    }

    function abortActiveFetch() {
      if (activeController) activeController.abort();
      activeController = null;
    }

    function stopPolling() {
      if (pollTimer !== null) {
        window.clearInterval(pollTimer);
        pollTimer = null;
      }
      abortActiveFetch();
    }

    function startPolling() {
      if (pollTimer === null && !document.hidden && !isResizing) {
        pollTimer = window.setInterval(tick, POLL_MS);
      }
    }

    function settleResize() {
      isResizing = false;
      applyLayoutProfile();
      redrawCharts();
      if (!document.hidden) {
        setFeedState('connecting');
        tick();
        startPolling();
      }
    }

    function pauseForResize() {
      if (document.hidden) return;
      isResizing = true;
      setFeedState('resizing');
      stopPolling();
      if (resizeTimer !== null) window.clearTimeout(resizeTimer);
      resizeTimer = window.setTimeout(settleResize, RESIZE_SETTLE_MS);
    }

    function handleResize() {
      if (resizeFrame !== null) return;
      resizeFrame = window.requestAnimationFrame(() => {
        resizeFrame = null;
        applyLayoutProfile();
        redrawCharts();
        pauseForResize();
      });
    }

    async function tick() {
      if (document.hidden || isResizing || inFlight) return;
      activeController = new AbortController();
      inFlight = true;
      try {
        const response = await fetch('/api/telemetry', {
          cache: 'no-store',
          signal: activeController.signal,
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        render(await response.json());
      } catch (error) {
        if ((!error || error.name !== 'AbortError') && !isResizing && !document.hidden) {
          setFeedState('offline');
        }
      } finally {
        activeController = null;
        inFlight = false;
      }
    }

    window.addEventListener('resize', handleResize, { passive: true });
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        stopPolling();
        setFeedState('paused');
        return;
      }
      applyLayoutProfile();
      tick();
      startPolling();
    });

    if ('ResizeObserver' in window) {
      new ResizeObserver(handleResize).observe(document.querySelector('main'));
    }

    document.querySelectorAll('.view-button').forEach(button => {
      button.addEventListener('click', () => setActiveView(button.dataset.view));
    });

    window.__piTelemetryStatus = () => ({
      feedState,
      polling: pollTimer !== null,
      resizing: isResizing,
      inFlight,
      activeView,
      maxPoints,
      profile: document.documentElement.dataset.dashboardProfile,
      canvas: Array.from(document.querySelectorAll('canvas')).map(canvas => ({
        id: canvas.id,
        width: canvas.width,
        height: canvas.height,
        cssWidth: Math.round(canvas.getBoundingClientRect().width),
        cssHeight: Math.round(canvas.getBoundingClientRect().height),
      })),
    });

    applyLayoutProfile();
    setActiveView('host');
    tick();
    startPolling();
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

    def __init__(self, vcgencmd_path: str | None = None) -> None:
        self.cached_status: str | None = None
        self.cached_time: float = 0
        self.lock = threading.Lock()
        self.vcgencmd_path = vcgencmd_path or shutil.which("vcgencmd")

    def get_throttle_status(self) -> str:
        now = time.time()
        with self.lock:
            if self.cached_status is not None and (now - self.cached_time) < 10.0:
                return self.cached_status

            if self.vcgencmd_path is None:
                self.cached_status = "unavailable"
                self.cached_time = now
                return self.cached_status

            try:
                result = subprocess.run(
                    [self.vcgencmd_path, "get_throttled"],
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


def safe_int(value: object, default: int = 0) -> int:
    try:
        if value is None:
            return default
        if not isinstance(value, (str, bytes, bytearray, int, float)):
            return default
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return default


def safe_float(value: object, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        if not isinstance(value, (str, bytes, bytearray, int, float)):
            return default
        return float(value)
    except (TypeError, ValueError, OverflowError):
        return default


def safe_label(value: object, default: str = "unknown", limit: int = 80) -> str:
    text = str(value or "").strip()
    if not text:
        return default
    return text[:limit]


def safe_cwd_label(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return "unknown"
    label = Path(text).name or text.strip("/").split("/")[-1]
    return safe_label(label, limit=64)


def short_thread_id(value: object) -> str:
    return safe_label(value, default="unknown", limit=10)


def codex_timestamp_ms(
    updated_at_ms: object,
    updated_at: object,
    created_at_ms: object,
    created_at: object,
) -> int | None:
    for value in (updated_at_ms, created_at_ms):
        timestamp = safe_int(value, -1)
        if timestamp > 0:
            return timestamp

    for value in (updated_at, created_at):
        timestamp_seconds = safe_float(value, -1.0)
        if timestamp_seconds > 0:
            return int(timestamp_seconds * 1000)

    return None


def age_seconds_from_ms(timestamp_ms: int | None, sample_time: float) -> float | None:
    if timestamp_ms is None:
        return None
    return round(max(0.0, sample_time - (timestamp_ms / 1000)), 1)


def env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off", "disabled"}


def model_display_name(provider: object, model: object) -> str:
    provider_label = safe_label(provider, default="", limit=40)
    model_label = safe_label(model, default="unknown", limit=80)
    if provider_label:
        return f"{provider_label}/{model_label}"
    return model_label


def matches_codex_process(
    name: object,
    cmdline: object,
    marker: str = DEFAULT_CODEX_PROCESS_MARKER,
) -> bool:
    marker = marker.strip().lower()
    if not marker:
        return False
    parts = [str(name or "")]
    if isinstance(cmdline, (list, tuple)):
        parts.extend(str(item) for item in cmdline)
    elif cmdline:
        parts.append(str(cmdline))
    return marker in " ".join(parts).lower()


def empty_codex_process_snapshot() -> dict[str, object]:
    return {
        "count": 0,
        "cpu_percent": 0.0,
        "memory_percent": 0.0,
        "memory_bytes": 0,
        "top": [],
    }


def codex_process_snapshot(marker: str = DEFAULT_CODEX_PROCESS_MARKER) -> dict[str, object]:
    rows: list[dict[str, float | int | str]] = []
    total_cpu = 0.0
    total_memory_percent = 0.0
    total_memory_bytes = 0

    for proc in psutil.process_iter(["pid", "name", "cmdline", "cpu_percent", "memory_percent"]):
        try:
            info = proc.info
            if not matches_codex_process(info.get("name"), info.get("cmdline"), marker=marker):
                continue

            memory_info = proc.memory_info()
            cpu_percent = round(float(info.get("cpu_percent") or 0.0), 1)
            memory_percent = round(float(info.get("memory_percent") or 0.0), 1)
            rss = int(memory_info.rss)
            total_cpu += cpu_percent
            total_memory_percent += memory_percent
            total_memory_bytes += rss
            rows.append(
                {
                    "pid": int(info["pid"]),
                    "name": safe_label(info.get("name"), limit=64),
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory_percent,
                    "memory_bytes": rss,
                }
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError, TypeError):
            continue

    rows.sort(key=lambda item: (item["cpu_percent"], item["memory_bytes"]), reverse=True)
    return {
        "count": len(rows),
        "cpu_percent": round(total_cpu, 1),
        "memory_percent": round(total_memory_percent, 1),
        "memory_bytes": total_memory_bytes,
        "top": rows[:CODEX_PROCESS_LIMIT],
    }


def llm_pressure(processes: dict[str, object], tokens_per_minute: float) -> str:
    process_count = safe_int(processes.get("count"))
    cpu_percent = safe_float(processes.get("cpu_percent"))
    memory_bytes = safe_int(processes.get("memory_bytes"))
    if cpu_percent >= 150.0 or memory_bytes >= 1_000_000_000 or tokens_per_minute >= 100_000.0:
        return "heavy"
    if process_count > 0 or tokens_per_minute > 0:
        return "active"
    return "idle"


class CodexTelemetryState:
    """Metadata-only Codex CLI telemetry from local state tables."""

    def __init__(
        self,
        state_path: Path = CODEX_STATE_PATH,
        enabled: bool = True,
        process_marker: str = DEFAULT_CODEX_PROCESS_MARKER,
    ) -> None:
        self.state_path = state_path
        self.enabled = enabled
        self.process_marker = process_marker
        self.previous_total_tokens: int | None = None
        self.previous_sample_time: float | None = None
        self.lock = threading.Lock()

    def unavailable(
        self,
        processes: dict[str, object],
        warnings: list[str],
        sample_time: float,
    ) -> dict[str, object]:
        with self.lock:
            self.previous_total_tokens = None
            self.previous_sample_time = sample_time

        return {
            "available": False,
            "source": "codex-cli",
            "privacy": "metadata-only",
            "error": "codex metadata unavailable",
            "summary": {
                "thread_count": 0,
                "total_tokens": 0,
                "token_delta": 0,
                "tokens_per_minute": 0.0,
                "latest_activity_ms": None,
                "latest_activity_age_seconds": None,
                "dominant_model": "unknown",
                "cli_version": None,
                "pressure": llm_pressure(processes, 0.0),
            },
            "models": [],
            "recent_threads": [],
            "processes": processes,
            "warnings": warnings,
        }

    def snapshot(self) -> dict[str, object]:
        sample_time = time.time()
        if not self.enabled:
            disabled_warnings = ["LLM telemetry disabled by configuration."]
            return self.unavailable(empty_codex_process_snapshot(), disabled_warnings, sample_time)

        processes = codex_process_snapshot(marker=self.process_marker)
        warnings: list[str] = []

        if not self.state_path.exists():
            warnings.append("Codex state database was not found.")
            return self.unavailable(processes, warnings, sample_time)

        try:
            connection = sqlite3.connect(
                f"file:{self.state_path.as_posix()}?mode=ro",
                timeout=0.2,
                uri=True,
            )
        except (OSError, sqlite3.Error):
            warnings.append("Codex state database could not be opened.")
            return self.unavailable(processes, warnings, sample_time)

        try:
            connection.row_factory = sqlite3.Row
            summary = connection.execute(
                """
                SELECT
                    COUNT(*) AS thread_count,
                    COALESCE(SUM(tokens_used), 0) AS total_tokens,
                    MAX(COALESCE(
                        updated_at_ms,
                        CAST(updated_at * 1000 AS INTEGER),
                        created_at_ms,
                        CAST(created_at * 1000 AS INTEGER),
                        0
                    )) AS latest_activity_ms
                FROM threads
                """
            ).fetchone()
            model_rows = connection.execute(
                """
                SELECT
                    COALESCE(model_provider, '') AS model_provider,
                    COALESCE(model, 'unknown') AS model,
                    COUNT(*) AS thread_count,
                    COALESCE(SUM(tokens_used), 0) AS tokens_used
                FROM threads
                GROUP BY model_provider, model
                ORDER BY tokens_used DESC, thread_count DESC
                LIMIT ?
                """,
                (CODEX_MODEL_LIMIT,),
            ).fetchall()
            recent_rows = connection.execute(
                """
                SELECT
                    id,
                    created_at,
                    updated_at,
                    created_at_ms,
                    updated_at_ms,
                    model_provider,
                    model,
                    tokens_used,
                    cwd,
                    cli_version
                FROM threads
                ORDER BY COALESCE(
                    updated_at_ms,
                    CAST(updated_at * 1000 AS INTEGER),
                    created_at_ms,
                    CAST(created_at * 1000 AS INTEGER),
                    0
                ) DESC
                LIMIT ?
                """,
                (CODEX_THREAD_LIMIT,),
            ).fetchall()
            cli_row = connection.execute(
                """
                SELECT cli_version
                FROM threads
                WHERE cli_version IS NOT NULL AND cli_version != ''
                ORDER BY COALESCE(
                    updated_at_ms,
                    CAST(updated_at * 1000 AS INTEGER),
                    created_at_ms,
                    CAST(created_at * 1000 AS INTEGER),
                    0
                ) DESC
                LIMIT 1
                """
            ).fetchone()
        except sqlite3.Error:
            warnings.append("Codex state database could not be read.")
            return self.unavailable(processes, warnings, sample_time)
        finally:
            connection.close()

        if summary is None:
            warnings.append("Codex state database returned no thread summary.")
            return self.unavailable(processes, warnings, sample_time)

        thread_count = safe_int(summary["thread_count"])
        total_tokens = safe_int(summary["total_tokens"])
        latest_activity_ms = safe_int(summary["latest_activity_ms"], 0) or None
        latest_activity_age_seconds = age_seconds_from_ms(latest_activity_ms, sample_time)

        with self.lock:
            previous_total = self.previous_total_tokens
            previous_sample_time = self.previous_sample_time
            self.previous_total_tokens = total_tokens
            self.previous_sample_time = sample_time

        token_delta = 0
        tokens_per_minute = 0.0
        if previous_total is not None and previous_sample_time is not None:
            elapsed = max(sample_time - previous_sample_time, 0.001)
            token_delta = max(0, total_tokens - previous_total)
            tokens_per_minute = round((token_delta / elapsed) * 60, 1)

        models: list[dict[str, object]] = []
        for row in model_rows:
            models.append(
                {
                    "model_provider": safe_label(row["model_provider"], default="", limit=40),
                    "model": safe_label(row["model"], limit=80),
                    "display": model_display_name(row["model_provider"], row["model"]),
                    "thread_count": safe_int(row["thread_count"]),
                    "tokens_used": safe_int(row["tokens_used"]),
                }
            )

        recent_threads: list[dict[str, object]] = []
        for row in recent_rows:
            timestamp_ms = codex_timestamp_ms(
                row["updated_at_ms"],
                row["updated_at"],
                row["created_at_ms"],
                row["created_at"],
            )
            recent_threads.append(
                {
                    "thread_id": short_thread_id(row["id"]),
                    "model": model_display_name(row["model_provider"], row["model"]),
                    "tokens_used": safe_int(row["tokens_used"]),
                    "cwd": safe_cwd_label(row["cwd"]),
                    "updated_at_ms": timestamp_ms,
                    "age_seconds": age_seconds_from_ms(timestamp_ms, sample_time),
                }
            )

        dominant_model = str(models[0]["display"]) if models else "unknown"
        return {
            "available": True,
            "source": "codex-cli",
            "privacy": "metadata-only",
            "summary": {
                "thread_count": thread_count,
                "total_tokens": total_tokens,
                "token_delta": token_delta,
                "tokens_per_minute": tokens_per_minute,
                "latest_activity_ms": latest_activity_ms,
                "latest_activity_age_seconds": latest_activity_age_seconds,
                "dominant_model": dominant_model,
                "cli_version": (
                    safe_label(cli_row["cli_version"], default="", limit=32) if cli_row else None
                ),
                "pressure": llm_pressure(processes, tokens_per_minute),
            },
            "models": models,
            "recent_threads": recent_threads,
            "processes": processes,
            "warnings": warnings,
        }


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

    def __init__(
        self,
        throttle_cache: ThrottleCache,
        llm_state: CodexTelemetryState | None = None,
    ) -> None:
        self.previous_network: dict[str, object] | None = None
        self.lock = threading.Lock()
        self.throttle_cache = throttle_cache
        self.llm_state = llm_state or CodexTelemetryState()
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
            "llm": self.llm_state.snapshot(),
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

    def write_response_body(self, body: bytes) -> None:
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            return

    def send_json(self, payload: dict[str, object], write_body: bool = True) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if write_body:
            self.write_response_body(body)

    def send_html(self, write_body: bool = True) -> None:
        nonce = secrets.token_urlsafe(16)
        csp = (
            "default-src 'self'; "
            f"script-src 'nonce-{nonce}'; "
            f"style-src 'nonce-{nonce}'; "
            "connect-src 'self'; "
            "img-src 'self' data:; "
            "object-src 'none'; "
            "base-uri 'none'; "
            "frame-ancestors 'none'"
        )
        body = HTML.replace("__CSP_NONCE__", nonce).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", csp)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if write_body:
            self.write_response_body(body)

    def send_not_found(self, write_body: bool = True) -> None:
        escaped_path = html.escape(self.path)
        body = f"Not found: {escaped_path}\n".encode("utf-8")
        self.send_response(HTTPStatus.NOT_FOUND)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if write_body:
            self.write_response_body(body)

    def send_route(self, write_body: bool = True) -> None:
        if self.path in {"/", "/index.html"}:
            self.send_html(write_body=write_body)
            return
        if self.path == "/api/telemetry":
            self.send_json(self.state.snapshot(), write_body=write_body)
            return
        if self.path == "/health":
            self.send_json({"ok": True}, write_body=write_body)
            return

        self.send_not_found(write_body=write_body)

    def do_GET(self) -> None:
        self.send_route()

    def do_HEAD(self) -> None:
        self.send_route(write_body=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve a lightweight Pi telemetry dashboard.")
    parser.add_argument(
        "--host",
        default=os.environ.get("PI_TELEMETRY_BIND", DEFAULT_HOST),
        help="Bind address",
    )
    parser.add_argument(
        "--port",
        default=safe_int(os.environ.get("PI_TELEMETRY_PORT"), DEFAULT_PORT),
        type=int,
        help="Bind port",
    )
    parser.add_argument(
        "--llm-telemetry",
        default=env_bool("PI_TELEMETRY_LLM", True),
        action=argparse.BooleanOptionalAction,
        help="Enable metadata-only local LLM telemetry",
    )
    parser.add_argument(
        "--codex-state-path",
        default=os.environ.get("PI_TELEMETRY_CODEX_STATE", str(CODEX_STATE_PATH)),
        help="Path to the Codex CLI state SQLite database",
    )
    parser.add_argument(
        "--codex-process-marker",
        default=os.environ.get("PI_TELEMETRY_CODEX_PROCESS", DEFAULT_CODEX_PROCESS_MARKER),
        help="Case-insensitive process name/cmdline marker for local LLM processes",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    throttle_cache = ThrottleCache()
    llm_state = CodexTelemetryState(
        Path(args.codex_state_path).expanduser(),
        enabled=bool(args.llm_telemetry),
        process_marker=str(args.codex_process_marker),
    )
    state = TelemetryState(throttle_cache, llm_state=llm_state)

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
