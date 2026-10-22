import duckdb

con = duckdb.connect("test.duckdb")

tables = ["orders", "order_items", "products", "stores", "supplier_prices"]

for table in tables:
    count = con.execute(
        f"SELECT COUNT(*) FROM raw.{table}"
    ).fetchone()[0]

    print(f"{table}: {count} rows")
    print("\nSupplier columns:")
    print(con.execute("DESCRIBE raw.supplier_prices").fetchall())
    

con.close()