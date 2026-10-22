from pathlib import Path
from run import ingest

ingest(
    Path("data"),
    Path("test.duckdb")
)