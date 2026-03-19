# React + D3 Databricks Dashboard

A local dashboard that fetches data from a Databricks SQL Warehouse (or demo data), caches it locally, and visualizes it with a D3.js bar chart. Includes a **Connection** panel to verify the live Databricks link.

## Architecture

```
React (Vite) ──fetch /api/──▶ FastAPI ──▶ Local JSON cache (backend/data/)
                    │              │
                    │              └── POST /api/refresh ──▶ Databricks REST (Statement Execution API)
                    │
                    └── GET /api/connection ──▶ Live SELECT 1 to warehouse (proof of connection)
```

- **Data flow:** Refresh pulls from Databricks (with cold-warehouse polling), writes JSON under `backend/data/`. All chart data is served from that cache.
- **Demo vs live:** The app always lists a **demo** table (`demo_galactic_pizzas`) with fake data, plus real tables (e.g. `trips`) after a refresh. The UI shows a **DEMO DATA** or **LIVE — Databricks** badge so the source is obvious.
- **Connection check:** The **Databricks Connection** panel runs a real `SELECT 1` against your warehouse and shows host, warehouse ID, latency, and timestamp.

## Data Sources

| Table | Source | Description |
|-------|--------|-------------|
| `demo_galactic_pizzas` | **Dummy** (static file) | Fake “galactic pizza” data (planets, delivery_minutes, tip_credits). No Databricks needed. |
| `trips` | **Databricks** | NYC taxi trips from `samples.nyctaxi.trips` (pickup/dropoff, distance, fare, zip codes). Fetched on Refresh. |

Real data is capped at **25 rows** per table for fast testing; the warehouse may take 10–30 seconds to wake up on first use.

## Prerequisites

- **Python 3.9+** with pip  
- **Node.js 18+** with npm  
- **Databricks workspace** with a SQL Warehouse  
- **Personal Access Token** (Databricks → Settings → Developer → Access tokens)

## Quick Start

### 1. Configure credentials

```bash
cp .env.example .env
# Edit .env with your Databricks host, token, and warehouse ID
```

`.env`:

```
DATABRICKS_HOST=https://<your-workspace>.cloud.databricks.com
DATABRICKS_TOKEN=dapi_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DATABRICKS_WAREHOUSE_ID=xxxxxxxxxxxxxxxx
DATABRICKS_CATALOG=samples
DATABRICKS_SCHEMA=nyctaxi
```

### 2. Start the backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API: `http://localhost:8000`. Docs: `http://localhost:8000/docs`.

The **demo** table works immediately (no Databricks). To load **live** data, click **⟳ Refresh data** in the UI; the first run may take 1–2 minutes if the warehouse is cold.

### 3. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. Use the table dropdown to switch between **DEMO** and **trips** (live). Use **Databricks Connection → Test Connection** to confirm the warehouse is reachable and see latency.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Cache status, tables, `refreshing`, `fetched_at` |
| GET | `/api/tables` | List tables and `sources` (dummy vs databricks) |
| GET | `/api/query/{table_name}?limit=25` | Rows for a table; response includes `source` |
| POST | `/api/refresh` | Trigger background fetch from Databricks (writes to cache) |
| GET | `/api/connection` | **Live** ping: runs `SELECT 1` on warehouse, returns host, warehouse_id, latency_ms, checked_at |

### Example responses

```json
GET /api/tables
{
  "tables": ["demo_galactic_pizzas", "trips"],
  "sources": {
    "demo_galactic_pizzas": "dummy",
    "trips": "databricks"
  }
}

GET /api/query/trips?limit=2
{
  "table": "trips",
  "source": "databricks",
  "count": 2,
  "data": [
    {
      "tpep_pickup_datetime": "2016-02-13T21:47:53.000Z",
      "tpep_dropoff_datetime": "2016-02-13T21:57:15.000Z",
      "trip_distance": 1.4,
      "fare_amount": 8.0,
      "pickup_zip": 10103,
      "dropoff_zip": 10110
    }
  ]
}

GET /api/connection
{
  "host": "https://xxx.cloud.databricks.com",
  "warehouse_id": "b01b74cbd32bcd92",
  "catalog": "samples",
  "schema": "nyctaxi",
  "token_set": true,
  "ping": "ok",
  "latency_ms": 15234,
  "checked_at": "2026-03-19T14:30:00.000000+00:00"
}
```

## Project Structure

```
react_d3_databricks/
├── frontend/
│   ├── src/
│   │   ├── App.jsx       # Table picker, source badge, bar chart, connection panel
│   │   ├── main.jsx
│   │   └── index.css
│   ├── vite.config.js    # Proxies /api → localhost:8000
│   └── package.json
├── backend/
│   ├── main.py           # FastAPI: health, tables, query, refresh, connection
│   ├── db.py             # Databricks REST (Statement Execution API), polling for cold warehouse
│   ├── cache.py         # JSON cache in data/, manifest with sources, fetch_and_cache
│   ├── data/             # Generated: _manifest.json, demo_galactic_pizzas.json, trips.json (gitignored)
│   └── requirements.txt
├── .env.example
├── .env                  # Your credentials (gitignored)
└── README.md
```

## Troubleshooting

- **“Cache is empty” / no tables**  
  Click **⟳ Refresh data** once. Ensure the backend is running and `.env` has valid `DATABRICKS_HOST`, `DATABRICKS_TOKEN`, `DATABRICKS_WAREHOUSE_ID`. The demo table appears even without a successful refresh.

- **Refresh takes 1–2 minutes**  
  Normal when the SQL warehouse is cold. The UI shows “Warehouse is waking up…” and polls until the cache is filled.

- **Want to confirm live data**  
  Select the `trips` table (not the demo one), check the **LIVE — Databricks** badge, and use **Databricks Connection → Test Connection** to see the live `SELECT 1` result and latency.
