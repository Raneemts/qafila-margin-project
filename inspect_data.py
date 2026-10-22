import sqlite3

conn = sqlite3.connect("data/qafila_oltp.sqlite")

tables = ["orders", "order_items", "products", "stores"]

for table in tables:
    print(f"\n--- {table} ---")

    columns = conn.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()

    for column in columns:
        print(f"{column[1]} : {column[2]}")

conn.close()

from pathlib import Path

supplier_dir = Path("data/suppliers")

for file in sorted(supplier_dir.glob("prices_*.csv")):
    print(f"\n--- {file.name} ---")

    with open(file, "r", encoding="utf-8-sig") as f:
        for i, line in enumerate(f):
            if i >= 5:
                break
            print(repr(line.strip()))