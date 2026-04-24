"""Database connection helper — one place to change if we switch to Snowflake later."""
import psycopg2
from psycopg2.extras import execute_values

DB_CONFIG = {
    "dbname": "billgo_analytics",
    "user": "veda",
    "host": "localhost",
    "port": 5432,
}


def get_connection():
    """Opens a new Postgres connection."""
    return psycopg2.connect(**DB_CONFIG)


def bulk_insert(conn, table, columns, rows):
    """
    Inserts many rows fast using execute_values.
    Why not one-by-one: inserting 250k rows one at a time takes ~10 minutes.
    With execute_values it's much faster.
    """
    if not rows:
        return
    placeholders = ",".join(columns)
    sql = f"INSERT INTO {table} ({placeholders}) VALUES %s"
    with conn.cursor() as cur:
        execute_values(cur, sql, rows, page_size=1000)
    conn.commit()
    print(f"  ✓ inserted {len(rows):,} rows into {table}")
