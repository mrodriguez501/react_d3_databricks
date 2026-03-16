# React + D3 Databricks Dashboard

A local dashboard that queries a Databricks SQL Warehouse and visualizes the results with D3.js charts (bar, line, pie, scatter, KPI cards).

## Architecture

```
React (Vite) ──fetch /api/──▶ FastAPI ──databricks-sql-connector──▶ Databricks SQL Warehouse
```

## Prerequisites

- **Python 3.9+** with pip
- **Node.js 18+** with npm
- A **Databricks workspace** with a SQL Warehouse running
- A **Personal Access Token** (Databricks → Settings → Developer → Access tokens)
- At least one table or view to query

## Quick Start

### 1. Configure credentials

```bash
cp .env.example .env
# Edit .env with your Databricks host, token, warehouse ID, catalog, and schema
```

### 2. Start the backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

The API is now running at `http://localhost:8000`. Check `http://localhost:8000/docs` for the interactive Swagger UI.

### 3. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/tables` | List tables in the configured catalog/schema |
| GET | `/api/query/{table_name}` | Return up to 1000 rows from a table as JSON |

## Project Structure

```
react_d3_databricks/
├── frontend/              # React + Vite + D3
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── charts/       (BarChart, LineChart, PieChart, ScatterPlot, KpiCards)
│   │   │   └── layout/       (Header)
│   │   ├── hooks/useData.js
│   │   ├── App.jsx
│   │   └── main.jsx
│   └── vite.config.js
├── backend/
│   ├── main.py            # FastAPI routes
│   ├── db.py              # Databricks connection helper
│   └── requirements.txt
├── .env.example
└── README.md
```
