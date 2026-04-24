"""Shared pytest fixtures for data quality tests."""
import sys
from pathlib import Path

import pytest

# Add project root to Python path so tests can import generator.db
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from generator.db import get_connection


@pytest.fixture
def db():
    """Provide a live database connection to each test; close after."""
    conn = get_connection()
    yield conn
    conn.close()


def run_query(conn, sql):
    """Helper: execute a query and return all rows."""
    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall()


def run_scalar(conn, sql):
    """Helper: execute a query expected to return a single value."""
    with conn.cursor() as cur:
        cur.execute(sql)
        row = cur.fetchone()
        return row[0] if row else None
