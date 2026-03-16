import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

USE_DUMMY = os.getenv("USE_DUMMY", "true").lower() == "true"

if not USE_DUMMY:
    from db import list_tables, query_table

app = FastAPI(title="Databricks Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DUMMY_DATA = [
    {"month": "Jan", "region": "West",  "product": "Widget A", "units": 120, "revenue": 14400, "cost": 7200},
    {"month": "Jan", "region": "East",  "product": "Widget B", "units": 85,  "revenue": 12750, "cost": 6800},
    {"month": "Feb", "region": "West",  "product": "Widget A", "units": 145, "revenue": 17400, "cost": 8700},
    {"month": "Feb", "region": "East",  "product": "Widget B", "units": 92,  "revenue": 13800, "cost": 7360},
    {"month": "Mar", "region": "West",  "product": "Widget C", "units": 200, "revenue": 30000, "cost": 14000},
    {"month": "Mar", "region": "East",  "product": "Widget A", "units": 110, "revenue": 13200, "cost": 6600},
    {"month": "Apr", "region": "West",  "product": "Widget B", "units": 78,  "revenue": 11700, "cost": 6240},
    {"month": "Apr", "region": "East",  "product": "Widget C", "units": 165, "revenue": 24750, "cost": 11550},
    {"month": "May", "region": "West",  "product": "Widget A", "units": 190, "revenue": 22800, "cost": 11400},
    {"month": "May", "region": "East",  "product": "Widget B", "units": 105, "revenue": 15750, "cost": 8400},
    {"month": "Jun", "region": "West",  "product": "Widget C", "units": 230, "revenue": 34500, "cost": 16100},
    {"month": "Jun", "region": "East",  "product": "Widget A", "units": 140, "revenue": 16800, "cost": 8400},
    {"month": "Jul", "region": "West",  "product": "Widget B", "units": 98,  "revenue": 14700, "cost": 7840},
    {"month": "Jul", "region": "East",  "product": "Widget C", "units": 180, "revenue": 27000, "cost": 12600},
    {"month": "Aug", "region": "West",  "product": "Widget A", "units": 210, "revenue": 25200, "cost": 12600},
    {"month": "Aug", "region": "East",  "product": "Widget B", "units": 115, "revenue": 17250, "cost": 9200},
    {"month": "Sep", "region": "West",  "product": "Widget C", "units": 195, "revenue": 29250, "cost": 13650},
    {"month": "Sep", "region": "East",  "product": "Widget A", "units": 130, "revenue": 15600, "cost": 7800},
    {"month": "Oct", "region": "West",  "product": "Widget B", "units": 88,  "revenue": 13200, "cost": 7040},
    {"month": "Oct", "region": "East",  "product": "Widget C", "units": 220, "revenue": 33000, "cost": 15400},
    {"month": "Nov", "region": "West",  "product": "Widget A", "units": 175, "revenue": 21000, "cost": 10500},
    {"month": "Nov", "region": "East",  "product": "Widget B", "units": 125, "revenue": 18750, "cost": 10000},
    {"month": "Dec", "region": "West",  "product": "Widget C", "units": 260, "revenue": 39000, "cost": 18200},
    {"month": "Dec", "region": "East",  "product": "Widget A", "units": 155, "revenue": 18600, "cost": 9300},
]


@app.get("/api/tables")
def get_tables():
    if USE_DUMMY:
        return {"tables": ["demo_sales"]}
    try:
        return {"tables": list_tables()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/query/{table_name}")
def get_table_data(table_name: str, limit: int = 1000):
    if USE_DUMMY:
        rows = DUMMY_DATA[:limit]
        return {"table": table_name, "count": len(rows), "data": rows}
    try:
        rows = query_table(table_name, limit=limit)
        return {"table": table_name, "count": len(rows), "data": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
