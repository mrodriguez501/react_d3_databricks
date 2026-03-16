import { useState, useEffect, useRef } from "react";
import * as d3 from "d3";
import "./index.css";

export default function App() {
  const [tables, setTables] = useState([]);
  const [table, setTable] = useState("");
  const [data, setData] = useState([]);
  const [columns, setColumns] = useState([]);
  const [status, setStatus] = useState("Loading tables…");

  const barRef = useRef();
  const lineRef = useRef();
  const pieRef = useRef();
  const scatterRef = useRef();

  // Fetch table list on mount
  useEffect(() => {
    fetch("/api/tables")
      .then((r) => r.json())
      .then((j) => {
        setTables(j.tables);
        setStatus(null);
      })
      .catch((e) => setStatus(`Error: ${e.message}`));
  }, []);

  // Fetch rows when a table is selected
  useEffect(() => {
    if (!table) return;
    setStatus("Fetching data…");
    fetch(`/api/query/${table}?limit=200`)
      .then((r) => r.json())
      .then((j) => {
        setData(j.data);
        setColumns(j.data.length ? Object.keys(j.data[0]) : []);
        setStatus(null);
      })
      .catch((e) => setStatus(`Error: ${e.message}`));
  }, [table]);

  // Pick first numeric and first categorical column for quick charts
  const numCols = columns.filter((c) =>
    data.slice(0, 10).every((r) => r[c] === null || !isNaN(Number(r[c])))
  );
  const catCols = columns.filter((c) => !numCols.includes(c));
  const xCol = catCols[0] || columns[0];
  const yCol = numCols[0];

  // Redraw all four charts whenever data changes
  useEffect(() => {
    if (!data.length || !xCol || !yCol) return;

    drawBar(barRef.current, data, xCol, yCol);
    drawLine(lineRef.current, data, xCol, yCol);
    drawPie(pieRef.current, data, xCol, yCol);
    drawScatter(scatterRef.current, data, numCols[0], numCols[1] || numCols[0]);
  }, [data, xCol, yCol]);

  return (
    <div className="app">
      <header>
        <h1>Databricks + D3 Dashboard</h1>
      </header>

      <div className="toolbar">
        <select value={table} onChange={(e) => setTable(e.target.value)}>
          <option value="">-- pick a table --</option>
          {tables.map((t) => (
            <option key={t}>{t}</option>
          ))}
        </select>
        {status && <span className="status">{status}</span>}
      </div>

      {data.length > 0 && (
        <>
          <p className="meta">
            Showing <strong>{data.length}</strong> rows &middot; x = <code>{xCol}</code> &middot; y = <code>{yCol}</code>
          </p>

          <div className="grid">
            <section>
              <h2>Bar</h2>
              <svg ref={barRef} />
            </section>
            <section>
              <h2>Line</h2>
              <svg ref={lineRef} />
            </section>
            <section>
              <h2>Pie</h2>
              <svg ref={pieRef} />
            </section>
            <section>
              <h2>Scatter</h2>
              <svg ref={scatterRef} />
            </section>
          </div>
        </>
      )}
    </div>
  );
}

/* ── D3 draw helpers ─────────────────────────────────────── */

const W = 480, H = 300, M = { t: 20, r: 20, b: 50, l: 50 };

function drawBar(svg, data, xKey, yKey) {
  const el = d3.select(svg).attr("viewBox", `0 0 ${W} ${H}`);
  el.selectAll("*").remove();

  const iw = W - M.l - M.r, ih = H - M.t - M.b;
  const g = el.append("g").attr("transform", `translate(${M.l},${M.t})`);

  const x = d3.scaleBand().domain(data.map((d) => String(d[xKey]))).range([0, iw]).padding(0.2);
  const y = d3.scaleLinear().domain([0, d3.max(data, (d) => +d[yKey])]).nice().range([ih, 0]);

  g.append("g").attr("transform", `translate(0,${ih})`).call(d3.axisBottom(x)).selectAll("text").attr("transform", "rotate(-35)").style("text-anchor", "end");
  g.append("g").call(d3.axisLeft(y).ticks(5));

  g.selectAll("rect").data(data).join("rect")
    .attr("x", (d) => x(String(d[xKey]))).attr("width", x.bandwidth())
    .attr("y", ih).attr("height", 0).attr("rx", 3).attr("fill", "#6366f1")
    .transition().duration(500)
    .attr("y", (d) => y(+d[yKey])).attr("height", (d) => ih - y(+d[yKey]));
}

function drawLine(svg, data, xKey, yKey) {
  const el = d3.select(svg).attr("viewBox", `0 0 ${W} ${H}`);
  el.selectAll("*").remove();

  const iw = W - M.l - M.r, ih = H - M.t - M.b;
  const g = el.append("g").attr("transform", `translate(${M.l},${M.t})`);

  const x = d3.scalePoint().domain(data.map((d) => String(d[xKey]))).range([0, iw]);
  const y = d3.scaleLinear().domain([0, d3.max(data, (d) => +d[yKey])]).nice().range([ih, 0]);

  g.append("g").attr("transform", `translate(0,${ih})`).call(d3.axisBottom(x).tickValues(x.domain().filter((_, i) => i % Math.ceil(data.length / 8) === 0))).selectAll("text").attr("transform", "rotate(-35)").style("text-anchor", "end");
  g.append("g").call(d3.axisLeft(y).ticks(5));

  const line = d3.line().x((d) => x(String(d[xKey]))).y((d) => y(+d[yKey])).curve(d3.curveMonotoneX);
  const path = g.append("path").datum(data).attr("fill", "none").attr("stroke", "#06b6d4").attr("stroke-width", 2).attr("d", line);
  const len = path.node().getTotalLength();
  path.attr("stroke-dasharray", `${len} ${len}`).attr("stroke-dashoffset", len).transition().duration(700).attr("stroke-dashoffset", 0);
}

function drawPie(svg, data, labelKey, valueKey) {
  const size = 300;
  const el = d3.select(svg).attr("viewBox", `0 0 ${size} ${size}`);
  el.selectAll("*").remove();

  const radius = size / 2 - 10;
  const g = el.append("g").attr("transform", `translate(${size / 2},${size / 2})`);

  const agg = d3.rollups(data, (v) => d3.sum(v, (d) => +d[valueKey]), (d) => String(d[labelKey])).slice(0, 10);
  const color = d3.scaleOrdinal(d3.schemeTableau10);
  const pie = d3.pie().value((d) => d[1]).sort(null);
  const arc = d3.arc().innerRadius(radius * 0.5).outerRadius(radius);

  g.selectAll("path").data(pie(agg)).join("path")
    .attr("fill", (d) => color(d.data[0]))
    .transition().duration(500)
    .attrTween("d", function (d) { const i = d3.interpolate({ startAngle: 0, endAngle: 0 }, d); return (t) => arc(i(t)); });

  g.selectAll("text").data(pie(agg)).join("text")
    .attr("transform", (d) => `translate(${arc.centroid(d)})`)
    .attr("text-anchor", "middle").attr("dy", "0.35em").style("font-size", "10px").style("fill", "#fff")
    .text((d) => d.data[0]);
}

function drawScatter(svg, data, xKey, yKey) {
  const el = d3.select(svg).attr("viewBox", `0 0 ${W} ${H}`);
  el.selectAll("*").remove();

  if (!xKey || !yKey) return;

  const iw = W - M.l - M.r, ih = H - M.t - M.b;
  const g = el.append("g").attr("transform", `translate(${M.l},${M.t})`);

  const x = d3.scaleLinear().domain(d3.extent(data, (d) => +d[xKey])).nice().range([0, iw]);
  const y = d3.scaleLinear().domain(d3.extent(data, (d) => +d[yKey])).nice().range([ih, 0]);

  g.append("g").attr("transform", `translate(0,${ih})`).call(d3.axisBottom(x).ticks(5));
  g.append("g").call(d3.axisLeft(y).ticks(5));

  g.selectAll("circle").data(data).join("circle")
    .attr("cx", (d) => x(+d[xKey])).attr("cy", (d) => y(+d[yKey]))
    .attr("r", 0).attr("fill", "#f59e0b").attr("opacity", 0.7)
    .transition().duration(400).attr("r", 4);
}
