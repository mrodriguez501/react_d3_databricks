import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from cache import (
    cache_is_populated,
    fetch_and_cache,
    get_cached_data,
    get_cached_tables,
    get_table_source,
    read_manifest,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)-8s %(levelname)-5s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("api")
_pool = ThreadPoolExecutor(max_workers=2)
_refreshing = False

app = FastAPI(title="Databricks Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "message": "Databricks Dashboard API",
        "cache": cache_is_populated(),
        "docs": "/docs",
        "endpoints": ["/api/health", "/api/tables", "/api/query/{table_name}", "/api/refresh"],
    }


@app.get("/api/health")
def health():
    manifest = read_manifest()
    return {
        "status": manifest.get("status", "empty"),
        "cache": cache_is_populated(),
        "tables": manifest.get("tables", []),
        "fetched_at": manifest.get("fetched_at"),
        "refreshing": _refreshing,
        "error": manifest.get("error"),
    }


@app.get("/api/connection")
def connection_check():
    """Live ping to Databricks — proves the connection is real."""
    import time
    from db import HOST, WAREHOUSE_ID, CATALOG, SCHEMA, TOKEN, _execute_sql

    info = {
        "host": HOST,
        "warehouse_id": WAREHOUSE_ID,
        "catalog": CATALOG,
        "schema": SCHEMA,
        "token_set": bool(TOKEN),
    }
    start = time.time()
    try:
        _execute_sql("SELECT 1 AS ping")
        info["ping"] = "ok"
    except Exception as e:
        info["ping"] = "error"
        info["ping_error"] = str(e)
    info["latency_ms"] = round((time.time() - start) * 1000)
    info["checked_at"] = __import__("datetime").datetime.now(
        __import__("datetime").timezone.utc
    ).isoformat()
    return info


@app.get("/api/tables")
def get_tables():
    tables = get_cached_tables()
    if not tables:
        if _refreshing:
            return {"tables": [], "sources": {}, "status": "refreshing", "message": "Fetching data from Databricks — check back in a moment."}
        raise HTTPException(status_code=503, detail="Cache is empty. Click Refresh or POST /api/refresh to fetch data.")
    sources = {t: get_table_source(t) for t in tables}
    return {"tables": tables, "sources": sources}


@app.get("/api/query/{table_name}")
def get_table_data(table_name: str, limit: int = 25):
    result = get_cached_data(table_name, limit)
    if result is None:
        if _refreshing:
            raise HTTPException(status_code=202, detail="Data is being fetched — try again shortly.")
        raise HTTPException(status_code=404, detail=f"No cached data for '{table_name}'. POST /api/refresh first.")
    return result


@app.post("/api/refresh")
async def refresh():
    global _refreshing

    if _refreshing:
        return {"status": "already_running", "message": "A refresh is already in progress."}

    _refreshing = True

    async def _do_refresh():
        global _refreshing
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(_pool, fetch_and_cache)
        except Exception as e:
            log.error("Refresh failed: %s", e)
        finally:
            _refreshing = False

    asyncio.create_task(_do_refresh())

    return {
        "status": "started",
        "message": "Fetching data from Databricks in the background. Poll GET /api/health to check progress.",
    }
