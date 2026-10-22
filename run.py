"""Qafila gross margin pipeline: raw files -> DuckDB -> dbt -> Iceberg.

    uv run python run.py --data-dir data --warehouse warehouse

Must work on an empty warehouse folder, and must be safe to run again on the same one.
The grader runs it on a dataset you haven't seen, so never hard-code file names, row counts or SKUs.
"""

from __future__ import annotations

import pyarrow as pa
from pyiceberg.exceptions import NoSuchTableError
import csv
import pandas as pd
import sqlite3
import argparse
import os
import subprocess
import sys
from pathlib import Path

import duckdb
from pyiceberg.catalog.sql import SqlCatalog

DBT_DIR = Path(__file__).resolve().parent / "dbt"


def get_catalog(warehouse: Path) -> SqlCatalog:
    """The Iceberg catalog the grader reads. Don't change the name, the URI or the warehouse."""
    warehouse.mkdir(parents=True, exist_ok=True)
    return SqlCatalog("qafila", uri=f"sqlite:///{(warehouse / 'catalog.db').as_posix()}", warehouse=warehouse.resolve().as_posix())


def ingest(data_dir: Path, db: Path) -> None:
    sqlite_path = data_dir / "qafila_oltp.sqlite"

    tables = ["orders", "order_items", "products", "stores"]

    with sqlite3.connect(str(sqlite_path)) as source:
        with duckdb.connect(str(db)) as con:
            con.execute("CREATE SCHEMA IF NOT EXISTS raw")

            # Step 1: Load SQLite tables
            for table in tables:
                df = pd.read_sql_query(
                    f"SELECT * FROM {table}",
                    source
                )

                con.register("source_df", df)

                con.execute(
                    f"CREATE OR REPLACE TABLE raw.{table} AS "
                    "SELECT * FROM source_df"
                )

                con.unregister("source_df")

                print(f"Loaded {table}: {len(df)} rows")

            # Step 2: Load supplier CSV files
            supplier_rows = []

            supplier_dir = data_dir / "suppliers"

            for file in sorted(supplier_dir.glob("prices_*.csv")):

                with open(file, "r", encoding="utf-8-sig", newline="") as f:
                    reader = csv.DictReader(f)

                    for row in reader:
                        raw_cost = row.get("unit_cost")

                        if raw_cost is None:
                            raw_cost = row.get("cost_sar")

                        supplier_rows.append({
                            "source_file": file.name,
                            "supplier_id": row.get("supplier_id"),
                            "sku": row.get("sku"),
                            "valid_from": row.get("valid_from"),
                            "raw_cost": raw_cost
                        })

            supplier_df = pd.DataFrame(
                supplier_rows,
                columns=[
                    "source_file",
                    "supplier_id",
                    "sku",
                    "valid_from",
                    "raw_cost"
                ]
            )

            con.register("supplier_df", supplier_df)

            con.execute("""
                CREATE OR REPLACE TABLE raw.supplier_prices AS
                SELECT * FROM supplier_df
            """)

            con.unregister("supplier_df")

            print(f"Loaded supplier prices: {len(supplier_df)} rows")



def transform(db: Path) -> None:
    """Steps 2-4: build and test the dbt project in dbt/ against the DuckDB file.

    dbt runs in its own process: in this one it would keep the DuckDB file open and block publish().
    """
    env = {**os.environ, "QAFILA_DUCKDB": str(db.resolve())}
    cmd = [sys.executable, "-c", "from dbt.cli.main import cli; cli()",
           "build", "--project-dir", str(DBT_DIR), "--profiles-dir", str(DBT_DIR)]
    if subprocess.run(cmd, env=env).returncode != 0:
        raise SystemExit("dbt build failed")


def publish(db: Path, warehouse: Path) -> None:
    catalog = get_catalog(warehouse)

    models = [
        ("silver", "product_cost_history"),
        ("gold", "weekly_margin"),
        ("quality", "price_quarantine"),
    ]

    def sorted_rows(table):
        return sorted(
            [str(row) for row in table.to_pylist()]
        )

    with duckdb.connect(str(db)) as con:
        for namespace, table_name in models:
            catalog.create_namespace_if_not_exists(namespace)

            arrow_table = con.execute(
                f"SELECT * FROM {namespace}.{table_name}"
            ).to_arrow_table()

            identifier = f"{namespace}.{table_name}"

            try:
                iceberg_table = catalog.load_table(identifier)

                # Compare existing data with new data
                existing_table = iceberg_table.scan().to_arrow()

                if sorted_rows(existing_table) == sorted_rows(arrow_table):
                    print(f"No changes: {identifier}")

                else:
                    # Update without deleting the Iceberg table
                    iceberg_table.overwrite(arrow_table)
                    print(f"Updated Iceberg table: {identifier}")

            except NoSuchTableError:
                # Create table only on the first run
                iceberg_table = catalog.create_table(
                    identifier,
                    schema=arrow_table.schema,
                )

                iceberg_table.append(arrow_table)
                print(f"Created Iceberg table: {identifier}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data-dir", type=Path, default=Path("data"))
    ap.add_argument("--warehouse", type=Path, default=Path("warehouse"))
    args = ap.parse_args()

    args.warehouse.mkdir(parents=True, exist_ok=True)
    db = args.warehouse / "qafila.duckdb"
    ingest(args.data_dir, db)
    transform(db)
    publish(db, args.warehouse)
    print(f"done: {args.warehouse.resolve()}")


if __name__ == "__main__":
    main()
