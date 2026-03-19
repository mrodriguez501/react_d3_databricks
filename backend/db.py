"""
Databricks SQL via REST API (Statement Execution API 2.0).

Uses the same REST endpoint that worked via curl — no Python connector needed.
Handles warehouse cold-starts by polling until the statement completes.
"""

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

HOST = os.getenv("DATABRICKS_HOST", "").rstrip("/")
TOKEN = os.getenv("DATABRICKS_TOKEN", "")
WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID", "")
CATALOG = os.getenv("DATABRICKS_CATALOG", "samples")
SCHEMA = os.getenv("DATABRICKS_SCHEMA", "nyctaxi")

_HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
_STATEMENTS_URL = f"{HOST}/api/2.0/sql/statements"

POLL_INTERVAL = 5
MAX_WAIT = 300


def _execute_sql(statement: str) -> dict:
    """Submit SQL, poll until done, return the full response JSON."""
    resp = requests.post(
        _STATEMENTS_URL,
        headers=_HEADERS,
        json={
            "warehouse_id": WAREHOUSE_ID,
            "catalog": CATALOG,
            "schema": SCHEMA,
            "statement": statement,
            "wait_timeout": "0s",
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    stmt_id = data["statement_id"]
    state = data["status"]["state"]
    waited = 0

    while state in ("PENDING", "RUNNING") and waited < MAX_WAIT:
        time.sleep(POLL_INTERVAL)
        waited += POLL_INTERVAL
        poll = requests.get(
            f"{_STATEMENTS_URL}/{stmt_id}",
            headers=_HEADERS,
            timeout=30,
        )
        poll.raise_for_status()
        data = poll.json()
        state = data["status"]["state"]

    if state != "SUCCEEDED":
        error = data.get("status", {}).get("error", {}).get("message", state)
        raise RuntimeError(f"SQL statement {state}: {error}")

    return data


def _rows_from_response(data: dict) -> list[dict]:
    """Convert Statement Execution API response to list of dicts."""
    columns = [c["name"] for c in data["manifest"]["schema"]["columns"]]
    raw_rows = data.get("result", {}).get("data_array", [])
    rows = []
    for raw in raw_rows:
        row = {}
        for col_name, val in zip(columns, raw):
            if val is None:
                row[col_name] = None
            else:
                try:
                    row[col_name] = int(val)
                except (ValueError, TypeError):
                    try:
                        row[col_name] = float(val)
                    except (ValueError, TypeError):
                        row[col_name] = val
        rows.append(row)
    return rows


def check_health() -> dict:
    info = {
        "host": HOST,
        "warehouse_id": WAREHOUSE_ID,
        "catalog": CATALOG,
        "schema": SCHEMA,
        "token_set": bool(TOKEN),
    }
    try:
        _execute_sql("SELECT 1")
        info["status"] = "ok"
    except Exception as e:
        info["status"] = "error"
        info["error"] = f"{type(e).__name__}: {e}"
    return info


def list_tables() -> list[str]:
    data = _execute_sql(f"SHOW TABLES IN {CATALOG}.{SCHEMA}")
    columns = [c["name"] for c in data["manifest"]["schema"]["columns"]]
    raw_rows = data.get("result", {}).get("data_array", [])
    name_idx = columns.index("tableName") if "tableName" in columns else 1
    return [row[name_idx] for row in raw_rows]


def query_table(table_name: str, limit: int = 25) -> list[dict]:
    safe = table_name.replace(";", "").replace("--", "")
    fqn = f"{CATALOG}.{SCHEMA}.{safe}"
    data = _execute_sql(f"SELECT * FROM {fqn} LIMIT {limit}")
    return _rows_from_response(data)
