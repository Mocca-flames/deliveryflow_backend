"""Development-only request/response inspector.

Stores the last N requests in memory and serves a lightweight HTML UI
at /__debug__ so you can inspect payloads without ngrok or print().

Active only when Settings.DEBUG is True.
"""

from __future__ import annotations

import json
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import HTMLResponse

_MAX_ENTRIES = 50

# In-memory ring buffer shared across requests.
_entries: deque[dict[str, Any]] = deque(maxlen=_MAX_ENTRIES)


# ── Middleware ──────────────────────────────────────────────────────────

class RequestInspectorMiddleware(BaseHTTPMiddleware):
    """Captures every request/response pair into _entries."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip debug UI endpoints to avoid recursion and noise.
        if request.url.path.startswith("/__debug__"):
            return await call_next(request)

        start = time.perf_counter()
        body_bytes = await request.body()
        status_code = 500
        response_body = b""

        try:
            response = await call_next(request)
            status_code = response.status_code

            # Attempt to read the response body for logging.
            # StreamingResponse doesn't allow .body(), so we capture what we can.
            if hasattr(response, "body"):
                response_body = response.body
            elif hasattr(response, "body_iterator"):
                chunks: list[bytes] = []
                async for chunk in response.body_iterator:
                    chunks.append(chunk if isinstance(chunk, bytes) else chunk.encode())
                response_body = b"".join(chunks)
                # Re-build a fresh StreamingResponse so the client still gets data.
                from starlette.responses import StreamingResponse
                response = StreamingResponse(
                    iter([response_body]),
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )
        except Exception:
            raise
        finally:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 1)

            entry = _build_entry(
                request=request,
                body_bytes=body_bytes,
                status_code=status_code,
                response_body=response_body,
                elapsed_ms=elapsed_ms,
            )
            _entries.appendleft(entry)

        return response


# ── Helpers ────────────────────────────────────────────────────────────

def _build_entry(
    *,
    request: Request,
    body_bytes: bytes,
    status_code: int,
    response_body: bytes,
    elapsed_ms: float,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)

    # Parse request body
    req_json: Any = None
    if body_bytes:
        try:
            req_json = json.loads(body_bytes)
        except (json.JSONDecodeError, UnicodeDecodeError):
            req_json = body_bytes.decode("utf-8", errors="replace")

    # Parse response body
    res_json: Any = None
    if response_body:
        try:
            res_json = json.loads(response_body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            res_json = response_body.decode("utf-8", errors="replace")

    # Headers — drop auth tokens for safety
    headers = dict(request.headers)
    if "authorization" in headers:
        headers["authorization"] = "Bearer ***"

    return {
        "ts": now.isoformat(),
        "time": now.strftime("%H:%M:%S"),
        "method": request.method,
        "path": str(request.url.path),
        "query": str(request.query_params) if request.query_params else None,
        "status": status_code,
        "elapsed_ms": elapsed_ms,
        "headers": headers,
        "req_body": req_json,
        "res_body": res_json,
    }


def get_entries() -> list[dict[str, Any]]:
    return list(_entries)


# ── HTML UI ────────────────────────────────────────────────────────────

_DEBUG_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>API Request Inspector</title>
<style>
  :root {
    --bg: #0d1117; --surface: #161b22; --border: #30363d;
    --text: #e6edf3; --muted: #8b949e; --accent: #58a6ff;
    --green: #3fb950; --red: #f85149; --yellow: #d29922; --orange: #db6d28;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', monospace; background: var(--bg); color: var(--text); font-size: 13px; }
  .header { padding: 16px 24px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 12px; }
  .header h1 { font-size: 16px; font-weight: 600; }
  .header .badge { background: var(--accent); color: var(--bg); padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 700; }
  .header .live { color: var(--green); font-size: 12px; }
  .toolbar { padding: 8px 24px; border-bottom: 1px solid var(--border); display: flex; gap: 8px; align-items: center; }
  .toolbar input { background: var(--surface); border: 1px solid var(--border); color: var(--text); padding: 4px 10px; border-radius: 6px; font-family: inherit; font-size: 12px; width: 220px; }
  .toolbar select { background: var(--surface); border: 1px solid var(--border); color: var(--text); padding: 4px 8px; border-radius: 6px; font-family: inherit; font-size: 12px; }
  .toolbar button { background: var(--surface); border: 1px solid var(--border); color: var(--muted); padding: 4px 10px; border-radius: 6px; cursor: pointer; font-family: inherit; font-size: 12px; }
  .toolbar button:hover { color: var(--text); border-color: var(--accent); }
  .list { overflow-y: auto; }
  .entry { display: flex; align-items: center; gap: 12px; padding: 8px 24px; border-bottom: 1px solid var(--border); cursor: pointer; transition: background .1s; }
  .entry:hover { background: var(--surface); }
  .entry.active { background: var(--surface); border-left: 3px solid var(--accent); }
  .entry .method { font-weight: 700; width: 52px; text-align: center; padding: 2px 0; border-radius: 4px; font-size: 11px; }
  .method-GET { color: var(--green); }
  .method-POST { color: var(--yellow); }
  .method-PUT { color: var(--orange); }
  .method-DELETE { color: var(--red); }
  .method-PATCH { color: var(--accent); }
  .entry .path { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .entry .status { width: 36px; text-align: center; font-weight: 700; }
  .status-ok { color: var(--green); }
  .status-err { color: var(--red); }
  .status-warn { color: var(--yellow); }
  .entry .time { color: var(--muted); width: 64px; text-align: right; }
  .entry .ms { color: var(--muted); width: 60px; text-align: right; }
  .detail { display: none; border-bottom: 1px solid var(--border); }
  .detail.open { display: block; }
  .detail-inner { padding: 16px 24px; }
  .detail-section { margin-bottom: 16px; }
  .detail-section h3 { font-size: 11px; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); margin-bottom: 6px; }
  pre { background: var(--surface); border: 1px solid var(--border); border-radius: 6px; padding: 12px; overflow-x: auto; white-space: pre-wrap; word-break: break-word; max-height: 400px; overflow-y: auto; }
  .empty { text-align: center; padding: 60px; color: var(--muted); }
</style>
</head>
<body>
<div class="header">
  <h1>API Request Inspector</h1>
  <span class="badge" id="count">0</span>
  <span class="live">&#9679; Live</span>
</div>
<div class="toolbar">
  <input id="search" placeholder="Filter by path..." />
  <select id="method-filter">
    <option value="">All methods</option>
    <option value="GET">GET</option>
    <option value="POST">POST</option>
    <option value="PUT">PUT</option>
    <option value="DELETE">DELETE</option>
    <option value="PATCH">PATCH</option>
  </select>
  <select id="status-filter">
    <option value="">All statuses</option>
    <option value="2xx">2xx</option>
    <option value="4xx">4xx</option>
    <option value="5xx">5xx</option>
  </select>
  <button onclick="refresh()">Refresh</button>
  <button onclick="clearEntries()">Clear</button>
</div>
<div class="list" id="list"></div>

<script>
let entries = [];
let openIdx = null;

async function refresh() {
  const res = await fetch('/__debug__/json');
  entries = await res.json();
  render();
}

function clearEntries() {
  entries = [];
  openIdx = null;
  render();
}

function matchesFilters(e) {
  const search = document.getElementById('search').value.toLowerCase();
  const method = document.getElementById('method-filter').value;
  const status = document.getElementById('status-filter').value;
  if (search && !e.path.toLowerCase().includes(search)) return false;
  if (method && e.method !== method) return false;
  if (status === '2xx' && (e.status < 200 || e.status >= 300)) return false;
  if (status === '4xx' && (e.status < 400 || e.status >= 500)) return false;
  if (status === '5xx' && (e.status < 500)) return false;
  return true;
}

function render() {
  const list = document.getElementById('list');
  const filtered = entries.filter(matchesFilters);
  document.getElementById('count').textContent = filtered.length;

  let html = '';
  filtered.forEach((e, i) => {
    const methodClass = 'method-' + e.method;
    const statusClass = e.status < 300 ? 'status-ok' : e.status < 500 ? 'status-warn' : 'status-err';
    const isActive = openIdx === i;

    html += '<div class="entry' + (isActive ? ' active' : '') + '" onclick="toggle(' + i + ')">';
    html += '<span class="method ' + methodClass + '">' + e.method + '</span>';
    html += '<span class="path">' + e.path + (e.query ? '?' + e.query : '') + '</span>';
    html += '<span class="status ' + statusClass + '">' + e.status + '</span>';
    html += '<span class="ms">' + e.elapsed_ms + 'ms</span>';
    html += '<span class="time">' + e.time + '</span>';
    html += '</div>';

    if (isActive) {
      html += '<div class="detail open"><div class="detail-inner">';
      html += section('Request Headers', JSON.stringify(e.headers, null, 2));
      if (e.req_body !== null) html += section('Request Body', JSON.stringify(e.req_body, null, 2));
      if (e.res_body !== null) html += section('Response (' + e.status + ')', JSON.stringify(e.res_body, null, 2));
      html += '</div></div>';
    }
  });

  if (!filtered.length) html = '<div class="empty">No requests captured yet.</div>';
  list.innerHTML = html;
}

function section(title, content) {
  return '<div class="detail-section"><h3>' + title + '</h3><pre>' + escapeHtml(content) + '</pre></div>';
}

function escapeHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function toggle(i) {
  openIdx = openIdx === i ? null : i;
  render();
}

document.getElementById('search').addEventListener('input', render);
document.getElementById('method-filter').addEventListener('change', render);
document.getElementById('status-filter').addEventListener('change', render);

refresh();
setInterval(refresh, 3000);
</script>
</body>
</html>
"""


def debug_ui_html() -> HTMLResponse:
    return HTMLResponse(content=_DEBUG_HTML)
