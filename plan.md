React + D3 Databricks Dashboard

Architecture





Frontend: React (Vite) + D3.js — full suite of visualizations (bar, line, pie, scatter, KPI cards)



Backend: FastAPI with databricks-sql-connector — thin data proxy, ~1-2 endpoint files



Config: .env file for Databricks credentials (host, token, warehouse ID, catalog/schema)

Project Structure

react_d3_databricks/
├── frontend/                # React + Vite app
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── charts/
│   │   │   │   ├── BarChart.jsx
│   │   │   │   ├── LineChart.jsx
│   │   │   │   ├── PieChart.jsx
│   │   │   │   ├── ScatterPlot.jsx
│   │   │   │   └── KpiCards.jsx
│   │   │   └── layout/
│   │   │       └── Header.jsx
│   │   ├── hooks/
│   │   │   └── useData.js       # Custom fetch hook
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js           # Proxy /api to FastAPI on :8000
├── backend/
│   ├── main.py                  # FastAPI app + routes
│   ├── db.py                    # Databricks connection helper
│   └── requirements.txt         # fastapi, uvicorn, databricks-sql-connector, python-dotenv
├── .env.example                 # Template for Databricks credentials
├── .gitignore
└── README.md                    # Setup instructions

Backend Details (backend/)





db.py — single function that opens a Databricks SQL connection using env vars (DATABRICKS_HOST, DATABRICKS_TOKEN, DATABRICKS_WAREHOUSE_ID, DATABRICKS_CATALOG, DATABRICKS_SCHEMA) and executes a query, returning rows as dicts.



main.py — FastAPI app with CORS middleware and a sample /api/query endpoint that accepts a table name parameter and returns JSON. A second endpoint /api/tables lists available tables.



requirements.txt — fastapi, uvicorn[standard], databricks-sql-connector, python-dotenv

Frontend Details (frontend/)





Vite dev server proxies /api/* requests to http://localhost:8000 (no CORS headaches in dev)



useData.js hook — generic fetch wrapper that calls the FastAPI endpoints and returns { data, loading, error }



Charts — each chart component receives data as a prop and renders using D3 (bindable to any dataset returned from Databricks):





BarChart.jsx — vertical/horizontal bar chart



LineChart.jsx — time series or continuous line chart



PieChart.jsx — pie/donut chart



ScatterPlot.jsx — scatter plot with tooltip



KpiCards.jsx — summary metric cards (count, avg, min, max, etc.)



Dashboard.jsx — orchestrates the layout, calls useData and distributes data to chart components



Modern, clean styling with CSS modules or a minimal stylesheet

Databricks Prerequisites (user must have)





A Databricks workspace with a SQL Warehouse running



A personal access token (Settings > Developer > Access tokens)



At least one table/view to query

How to Run Locally





Copy .env.example to .env and fill in Databricks credentials



cd backend && pip install -r requirements.txt && uvicorn main:app --reload



cd frontend && npm install && npm run dev



Open http://localhost:5173

