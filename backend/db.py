import os
from dotenv import load_dotenv
from databricks import sql

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

DATABRICKS_HOST = os.getenv("DATABRICKS_HOST", "")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN", "")
DATABRICKS_WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID", "")
DATABRICKS_CATALOG = os.getenv("DATABRICKS_CATALOG", "main")
DATABRICKS_SCHEMA = os.getenv("DATABRICKS_SCHEMA", "default")


def _get_connection():
    return sql.connect(
        server_hostname=DATABRICKS_HOST.replace("https://", ""),
        http_path=f"/sql/1.0/warehouses/{DATABRICKS_WAREHOUSE_ID}",
        access_token=DATABRICKS_TOKEN,
    )


def query_table(table_name: str, limit: int = 1000) -> list[dict]:
    """Return up to *limit* rows from a table as a list of dicts."""
    safe_table = table_name.replace(";", "").replace("--", "")
    fqn = f"{DATABRICKS_CATALOG}.{DATABRICKS_SCHEMA}.{safe_table}"

    with _get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT * FROM {fqn} LIMIT {limit}")
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]


def list_tables() -> list[str]:
    """Return table names in the configured catalog/schema."""
    with _get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"SHOW TABLES IN {DATABRICKS_CATALOG}.{DATABRICKS_SCHEMA}"
            )
            return [row.tableName for row in cursor.fetchall()]
