"""
Local JSON cache for Databricks data.

Flow:
  1. fetch_and_cache() pulls data from Databricks and writes JSON to backend/data/
  2. The API serves exclusively from those JSON files — instant responses.
  3. POST /api/refresh triggers a re-fetch in the background.
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)

MANIFEST_PATH = DATA_DIR / "_manifest.json"


def _table_path(table_name: str) -> Path:
    safe = table_name.replace("/", "_").replace("..", "_")
    return DATA_DIR / f"{safe}.json"


def read_manifest() -> dict:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text())
    return {}


DUMMY_TABLES = ["demo_galactic_pizzas"]


def _write_manifest(tables: list[str], status: str, error: str | None = None):
    sources = {t: "dummy" for t in DUMMY_TABLES}
    sources.update({t: "databricks" for t in tables if t not in DUMMY_TABLES})
    manifest = {
        "tables": DUMMY_TABLES + [t for t in tables if t not in DUMMY_TABLES],
        "sources": sources,
        "status": status,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "error": error,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))


def _serialize(value):
    """Convert non-JSON-serializable types (datetime, date, Decimal) to strings."""
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "__float__"):
        return float(value)
    return str(value)


def _normalize_row(row: dict) -> dict:
    return {k: _serialize(v) if not isinstance(v, (str, int, float, bool, type(None))) else v for k, v in row.items()}


def get_cached_tables() -> list[str]:
    manifest = read_manifest()
    tables = manifest.get("tables", [])
    for dt in DUMMY_TABLES:
        if dt not in tables and _table_path(dt).exists():
            tables.insert(0, dt)
    return tables


def get_table_source(table_name: str) -> str:
    manifest = read_manifest()
    return manifest.get("sources", {}).get(table_name, "dummy" if table_name in DUMMY_TABLES else "databricks")


def get_cached_data(table_name: str, limit: int = 1000) -> dict | None:
    path = _table_path(table_name)
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    rows = data["data"][:limit]
    source = get_table_source(table_name)
    return {"table": table_name, "source": source, "count": len(rows), "data": rows}


def fetch_and_cache(limit: int = 25) -> dict:
    """Pull tables + data from Databricks, write to local JSON, return summary."""
    import logging
    from db import list_tables, query_table

    log = logging.getLogger("cache")
    start = time.time()

    _write_manifest([], status="refreshing")
    log.info("Listing tables from Databricks (warehouse may be cold)…")

    try:
        tables = list_tables()
    except Exception as e:
        log.error("Failed to list tables: %s", e)
        _write_manifest([], status="error", error=str(e))
        raise

    log.info("Found %d table(s): %s", len(tables), tables)
    cached = []
    for t in tables:
        log.info("Fetching %s (limit %d)…", t, limit)
        try:
            rows = query_table(t, limit=limit)
        except Exception as e:
            log.error("Failed to fetch %s: %s", t, e)
            continue
        normalized = [_normalize_row(r) for r in rows]
        payload = {
            "table": t,
            "count": len(normalized),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "data": normalized,
        }
        _table_path(t).write_text(json.dumps(payload, indent=2))
        cached.append(t)
        log.info("Cached %s — %d rows", t, len(normalized))

    elapsed = round((time.time() - start) * 1000)
    _write_manifest(cached, status="ok")
    log.info("Done in %dms — cached tables: %s", elapsed, cached)

    return {
        "status": "ok",
        "tables": cached,
        "rows_per_table": limit,
        "elapsed_ms": elapsed,
    }


def cache_is_populated() -> bool:
    manifest = read_manifest()
    if manifest.get("status") == "ok" and len(manifest.get("tables", [])) > 0:
        return True
    return any(_table_path(dt).exists() for dt in DUMMY_TABLES)
