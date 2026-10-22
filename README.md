# Qafila gross margin

Submitted by: Raneem Alsaqat — academy: @SDAIAAcademy

The task, rules and grading are in [BRIEF.md](BRIEF.md).

```bash
uv sync
uv run python tools/make_data.py          # data/
uv run python run.py                      # data/ -> warehouse/ (DuckDB + Iceberg)
uv run python tools/check.py              # contract self-check
```

## Design

SQLite and CSV files → DuckDB raw tables → dbt staging views → dbt silver, gold and quality tables → Apache Iceberg using PyIceberg.

| Model | Layer | Grain (one row per ...) | Materialization |
|---|---|---|---|
| `stg_order_lines`, `stg_supplier_prices` | staging | Order line / supplier price record | dbt views |
| `product_cost_history` | silver | SKU and effective cost date | dbt table → Iceberg |
| `weekly_margin` | gold | ISO week, city and category | dbt table → Iceberg |
| `price_quarantine` | quality | Invalid supplier price record | dbt table → Iceberg |

**How the SCD2 history is built:** Supplier prices are cleaned and deduplicated by SKU and effective date, prioritizing the latest source file. Missing weeks keep the previous valid cost, and unchanged costs do not create new versions. The correction file overrides earlier prices for the same SKU and effective date.

**How each order line finds its cost:** Each delivered order line is matched to the historical cost valid on its Riyadh-local order date, using `valid_from` (inclusive) and `valid_to` (exclusive). Lines without a matching cost remain in total revenue but are excluded from costed revenue.

## Data problems I found

| Problem | Where | Rows affected | What I did |
|---|---|---|---|
| Unknown SKUs and invalid costs | Supplier CSV files | 7 | Quarantined invalid records with their original values |
| Different decimal formats | Supplier CSV files | Varies | Normalized comma decimals and Arabic-Indic digits |
| Duplicate and corrected prices | Supplier CSV files | Varies | Deduplicated by SKU and date, prioritizing the latest file |
| UTC vs. Riyadh dates | Order data | 31 order lines | Converted UTC timestamps to Riyadh time before filtering |

## Tests

| Test | On | What it protects against |
|---|---|---|
| `not_null` | `product_cost_history.sku` | Missing SKU |
| `not_null` | `product_cost_history.valid_from` | Missing effective date |
| `not_null` | `product_cost_history.unit_cost_sar` | Missing cost |
| `not_null` | `product_cost_history.is_current` | Missing current-version flag |
| `not_null` | `weekly_margin.iso_week` | Missing reporting week |
| `not_null` | `weekly_margin.city` | Missing city |
| `not_null` | `weekly_margin.category` | Missing category |
| `accepted_values` | `price_quarantine.reason` | Invalid quarantine reasons |

## Re-runs and the correction

Re-running the pipeline with unchanged data produced `No changes` for all three Iceberg tables, confirming idempotency. After applying the supplier correction, the cost history and weekly margin were updated while preserving older snapshots.

| Stage | Snapshot ID | Total margin (SAR) |
|---|---|---:|
| Before correction | 639471317284588676 | 800,660.04 |
| After correction | 1111525525032759664 | 803,159.50 |
| After Riyadh timezone fix | 6617708463969434286 | 803,515.80 |

The older Iceberg snapshot remains readable, demonstrating time travel. The pipeline passed **22/22 contract checks** and **8/8 dbt tests**.

## What I'd do next

With 100× more data, full-table processing would become slower and require more memory. I would implement incremental processing and partitioning. For daily supplier files, I would automate validation and improve handling of late-arriving corrections.

## AI assistance

I used ChatGPT to assist with Python and SQL implementation, debugging, and documentation. I ran the pipeline locally and verified the results using dbt tests and the provided checker.