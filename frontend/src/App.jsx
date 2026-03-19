import { useState, useEffect, useRef, useCallback } from "react";
import * as d3 from "d3";
import "./index.css";

const API_TIMEOUT = 120_000;

async function api(url, opts = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), API_TIMEOUT);
  try {
    const res = await fetch(url, { ...opts, signal: controller.signal });
    const body = await res.json().catch(() => null);
    if (!res.ok) throw new Error(body?.detail || `HTTP ${res.status}`);
    return body;
  } finally {
    clearTimeout(timer);
  }
}

export default function App() {
  const [tables, setTables] = useState([]);
  const [sources, setSources] = useState({});
  const [table, setTable] = useState("");
  const [dataSource, setDataSource] = useState(null);
  const [data, setData] = useState([]);
  const [columns, setColumns] = useState([]);
  const [status, setStatus] = useState("Loading tables…");
  const [refreshing, setRefreshing] = useState(false);
  const [conn, setConn] = useState(null);
  const [connLoading, setConnLoading] = useState(false);

  const barRef = useRef();

  const loadTables = useCallback(() => {
    setStatus("Loading tables…");
    api("/api/tables")
      .then((j) => {
        const t = j.tables ?? [];
        const src = j.sources ?? {};
        setTables(t);
        setSources(src);
        if (t.length > 0) {
          setStatus(null);
          if (!table && t.length >= 1) setTable(t[0]);
        } else if (j.status === "refreshing") {
          setStatus("Warehouse is waking up — this can take 1-2 min…");
          setRefreshing(true);
        } else {
          setStatus("No cached data. Click Refresh to fetch from Databricks.");
        }
      })
      .catch((e) => setStatus(`Error: ${e.message}`));
  }, []);

  useEffect(() => {
    loadTables();
  }, [loadTables]);

  useEffect(() => {
    if (!refreshing) return;
    const interval = setInterval(() => {
      api("/api/health")
        .then((h) => {
          if (!h.refreshing && h.cache) {
            setRefreshing(false);
            loadTables();
          }
        })
        .catch(() => {});
    }, 5000);
    return () => clearInterval(interval);
  }, [refreshing, loadTables]);

  useEffect(() => {
    if (!table) return;
    setStatus("Fetching rows…");
    api(`/api/query/${table}?limit=25`)
      .then((j) => {
        const rows = j.data ?? [];
        setData(rows);
        setDataSource(j.source ?? sources[table] ?? null);
        setColumns(rows.length ? Object.keys(rows[0]) : []);
        setStatus(null);
      })
      .catch((e) => setStatus(`Error: ${e.message}`));
  }, [table]);

  const triggerRefresh = useCallback(() => {
    setRefreshing(true);
    setStatus("Warehouse may be cold — fetching data (up to 2 min)…");
    api("/api/refresh", { method: "POST" }).catch((e) =>
      setStatus(`Error: ${e.message}`)
    );
  }, []);

  const pingDatabricks = useCallback(() => {
    setConnLoading(true);
    setConn(null);
    api("/api/connection")
      .then((c) => setConn(c))
      .catch((e) => setConn({ ping: "error", ping_error: e.message }))
      .finally(() => setConnLoading(false));
  }, []);

  const numCols = columns.filter((c) =>
    data.slice(0, 10).every((r) => r[c] === null || !isNaN(Number(r[c])))
  );
  const dateCols = columns.filter((c) =>
    data.slice(0, 5).some((r) => r[c] && !isNaN(Date.parse(String(r[c]))))
  );
  const continuousNum = numCols.filter((c) => !dateCols.includes(c));
  const groupCol =
    columns.find((c) => /zip/i.test(c) && !dateCols.includes(c)) ||
    columns[0];
  const yCol = continuousNum[0] || numCols[0];

  useEffect(() => {
    if (!data.length || !yCol || !barRef.current) return;

    const grouped = d3.rollups(
      data,
      (v) => d3.mean(v, (d) => +d[yCol]),
      (d) => String(d[groupCol])
    );
    const barData = grouped
      .sort((a, b) => b[1] - a[1])
      .slice(0, 20)
      .map(([key, val]) => ({ label: key, value: val }));

    drawBar(barRef.current, barData);
  }, [data, columns, groupCol, yCol]);

  const isError = status && status.startsWith("Error");

  return (
    <div className="app">
      <header>
        <h1>Databricks + D3 Dashboard</h1>
      </header>

      <div className="toolbar">
        <select value={table} onChange={(e) => setTable(e.target.value)}>
          <option value="">-- pick a table --</option>
          {tables.map((t) => (
            <option key={t} value={t}>
              {sources[t] === "dummy" ? `[DEMO] ${t}` : t}
            </option>
          ))}
        </select>

        {dataSource && (
          <span className={`source-badge ${dataSource === "dummy" ? "dummy" : "live"}`}>
            {dataSource === "dummy" ? "DEMO DATA" : "LIVE — Databricks"}
          </span>
        )}

        {status && (
          <span className={`status${isError ? " error" : ""}`}>{status}</span>
        )}

        {refreshing && <span className="spinner" />}

        <button
          className="refresh-btn"
          onClick={triggerRefresh}
          disabled={refreshing}
        >
          {refreshing ? "Refreshing…" : "⟳ Refresh data"}
        </button>

        {isError && !refreshing && (
          <button className="retry-btn" onClick={loadTables}>
            Retry
          </button>
        )}
      </div>

      {data.length > 0 && (
        <>
          <p className="meta">
            Showing <strong>{data.length}</strong> rows &middot; grouped by{" "}
            <code>{groupCol}</code> &middot; value = <code>{yCol}</code>
          </p>

          <div className="chart-container">
            <section>
              <h2>
                Avg {yCol} by {groupCol}
              </h2>
              <svg ref={barRef} />
            </section>
          </div>
        </>
      )}

      {data.length > 0 && (
        <details className="raw-data">
          <summary>Raw data ({data.length} rows)</summary>
          <pre>{JSON.stringify(data.slice(0, 5), null, 2)}</pre>
        </details>
      )}

      <div className="conn-panel">
        <div className="conn-header">
          <span className="conn-title">Databricks Connection</span>
          <button
            className="conn-ping-btn"
            onClick={pingDatabricks}
            disabled={connLoading}
          >
            {connLoading ? "Pinging…" : "Test Connection"}
          </button>
        </div>

        {connLoading && (
          <div className="conn-body">
            <span className="spinner" /> Sending <code>SELECT 1</code> to
            Databricks warehouse&hellip;
          </div>
        )}

        {conn && (
          <div className="conn-body">
            <div className={`conn-status ${conn.ping === "ok" ? "ok" : "fail"}`}>
              {conn.ping === "ok" ? "Connected" : "Failed"}
            </div>
            <table className="conn-table">
              <tbody>
                {conn.host && (
                  <tr><td>Host</td><td>{conn.host}</td></tr>
                )}
                {conn.warehouse_id && (
                  <tr><td>Warehouse</td><td><code>{conn.warehouse_id}</code></td></tr>
                )}
                {conn.catalog && (
                  <tr><td>Catalog / Schema</td><td>{conn.catalog}.{conn.schema}</td></tr>
                )}
                {conn.latency_ms != null && (
                  <tr><td>Round-trip</td><td>{conn.latency_ms.toLocaleString()} ms</td></tr>
                )}
                {conn.checked_at && (
                  <tr><td>Checked at</td><td>{new Date(conn.checked_at).toLocaleTimeString()}</td></tr>
                )}
                {conn.ping_error && (
                  <tr><td>Error</td><td className="conn-error">{conn.ping_error}</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

const W = 600,
  H = 340,
  M = { t: 20, r: 20, b: 70, l: 60 };

function drawBar(svg, barData) {
  if (!svg || !barData.length) return;
  const el = d3.select(svg).attr("viewBox", `0 0 ${W} ${H}`);
  el.selectAll("*").remove();
  const iw = W - M.l - M.r,
    ih = H - M.t - M.b;
  const g = el.append("g").attr("transform", `translate(${M.l},${M.t})`);
  const x = d3
    .scaleBand()
    .domain(barData.map((d) => d.label))
    .range([0, iw])
    .padding(0.2);
  const y = d3
    .scaleLinear()
    .domain([0, d3.max(barData, (d) => d.value)])
    .nice()
    .range([ih, 0]);
  g.append("g")
    .attr("transform", `translate(0,${ih})`)
    .call(d3.axisBottom(x))
    .selectAll("text")
    .attr("transform", "rotate(-40)")
    .style("text-anchor", "end");
  g.append("g").call(d3.axisLeft(y).ticks(5));
  g.selectAll("rect")
    .data(barData)
    .join("rect")
    .attr("x", (d) => x(d.label))
    .attr("width", x.bandwidth())
    .attr("y", ih)
    .attr("height", 0)
    .attr("rx", 3)
    .attr("fill", "#6366f1")
    .transition()
    .duration(500)
    .attr("y", (d) => y(d.value))
    .attr("height", (d) => ih - y(d.value));
}
