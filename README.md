# Azure Modern Data Platform
## Senior Data Engineer — Local Sandbox POC

> A fully working local implementation of a modern medallion data architecture using PySpark and Delta Lake — no Azure subscription required. Built to demonstrate production-grade data engineering patterns that map directly to Azure Databricks, ADLS Gen2, and Delta Live Tables.

---

## What This Demonstrates

| Pattern | Implementation |
|---|---|
| Medallion Architecture (Bronze → Silver → Gold) | Local PySpark + Delta Lake |
| Data quality enforcement | Filter/quarantine on null customer_id and negative sale_amount |
| ACID transactions on a data lake | Delta Lake write + MERGE operations |
| Time travel & audit history | `VERSION AS OF` on Silver table |
| Schema enforcement | Delta schema validation on write |
| Incremental-ready design | Idempotent writes, partition-ready structure |
| Infrastructure as code mindset | Reproducible, one-command pipeline run |

---

## Quick Start — Local Sandbox

No Azure account needed. Runs entirely on local PySpark with Delta Lake.

### Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.12 | Tested on macOS Apple Silicon |
| Java | 17+ (25 confirmed working) | Homebrew OpenJDK |
| Git | Any | |

> **Note on Java:** This setup was tested and confirmed working on **OpenJDK 25.0.2** (Homebrew). Do NOT set `JAVA_TOOL_OPTIONS` — leave JVM flags unset.

### Setup

```bash
# 1. Clone the repo
git clone https://github.com/bongaquino/azure-modern-data-platform.git
cd azure-modern-data-platform

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install --upgrade pip setuptools wheel
pip install pyspark==3.5.0 delta-spark==3.2.0 pandas numpy
```

> **Tip — Auto-activate venv on `cd`:** Add this to your `~/.zshrc` so the venv activates automatically whenever you enter any project folder:
> ```bash
> _auto_venv() {
>   if [[ -f ".venv/bin/activate" ]] && [[ "$VIRTUAL_ENV" != "$PWD/.venv" ]]; then
>     source .venv/bin/activate
>   elif [[ -n "$VIRTUAL_ENV" ]] && [[ "$PWD" != "$(dirname $VIRTUAL_ENV)"* ]]; then
>     deactivate
>   fi
> }
> function cd() { builtin cd "$@" && _auto_venv; }
> _auto_venv
> ```

---

## Running the Demo

### Step 1 — Generate test data

```bash
python3 sandbox/generate_test_data.py
```

Generates **525 retail sales records** across 3 batch CSV files:

- **500 valid records** — 5 Philippine regions, 3 customer segments (Premium/Standard/Budget), 5 product categories
- **25 intentionally bad records** — 12 negative sale amounts + 13 null customer IDs embedded to demonstrate quality enforcement

```
✓ Written 175 rows → sandbox/data/raw/sales/sales_batch_01.csv
✓ Written 175 rows → sandbox/data/raw/sales/sales_batch_02.csv
✓ Written 175 rows → sandbox/data/raw/sales/sales_batch_03.csv

500 good records + 25 bad records across 3 batch files.
```

### Step 2 — Run the medallion pipeline

```bash
python3 sandbox/pipelines/medallion_demo.py
```

Runs Bronze → Silver → Gold end-to-end:

**Bronze** — Raw ingestion, all 525 rows including bad records, Delta format written to `sandbox/data/bronze/sales`

**Silver** — Quality rules applied:
- `sale_amount > 0` enforced
- `customer_id IS NOT NULL` enforced
- Bad rows quarantined to `sandbox/data/quarantine/sales`

```
✓ Valid records passed to Silver : 500
✗ Bad records sent to Quarantine : 25
  Data quality rate              : 95.2%

+--------------------+-----+
|quarantine_reason   |count|
+--------------------+-----+
|negative_sale_amount|13   |
|null_customer_id    |12   |
+--------------------+-----+
```

**Gold** — Three business aggregation tables:

*Revenue by Customer Segment:*
```
+----------------+-------------+---------------+--------------------+
|customer_segment|total_revenue|avg_order_value|revenue_per_customer|
+----------------+-------------+---------------+--------------------+
|Standard        |3,186,993.37 |12,955.26      |13,061.45           |
|Premium         |2,189,099.34 |23,288.29      |23,288.29           |
|Budget          |972,535.16   |6,078.34       |6,078.34            |
+----------------+-------------+---------------+--------------------+
```

*Revenue by Region:*
```
+------------+-------------+------------+
|region      |total_revenue|total_orders|
+------------+-------------+------------+
|Davao       |1,664,780.33 |113         |
|Clark       |1,399,735.42 |110         |
|Cebu        |1,300,391.14 |101         |
|Iloilo      |1,017,960.72 |96          |
|Metro Manila|965,760.26   |80          |
+------------+-------------+------------+
```

*Monthly Revenue Trend (Jan–May 2025):*
```
+-------+---------------+------+
|month  |monthly_revenue|orders|
+-------+---------------+------+
|2025-01|1,312,227.89   |105   |
|2025-02|1,316,942.17   |87    |
|2025-03|1,414,104.45   |94    |
|2025-04|1,116,589.06   |103   |
|2025-05|1,188,764.30   |111   |
+-------+---------------+------+
```

### Step 3 — Delta Lake time travel demo

```bash
python3 sandbox/pipelines/delta_time_travel_demo.py
```

Demonstrates ACID transactions and historical versioning on the Silver table:

1. Reads current Silver table (Version 0 — 500 rows)
2. Applies a MERGE update — reclassifies Premium Metro Manila customers as VIP
3. Shows full Delta transaction log history
4. Queries `VERSION AS OF 0` (pre-update) vs current (post-update)
5. Displays the exact rows that changed between versions

```
── Delta Transaction Log History ──
+-------+---------------------+---------+------------------------------------------+
|version|timestamp            |operation|operationMetrics                          |
+-------+---------------------+---------+------------------------------------------+
|1      |2026-05-20 15:xx:xx  |UPDATE   |{numUpdatedRows -> N, numCopiedRows -> N} |
|0      |2026-05-20 15:xx:xx  |WRITE    |{numFiles -> 3, numOutputRows -> 500}     |
+-------+---------------------+---------+------------------------------------------+
```

### Full demo — one command

```bash
python3 sandbox/generate_test_data.py && \
python3 sandbox/pipelines/medallion_demo.py && \
python3 sandbox/pipelines/delta_time_travel_demo.py
```

---

## Architecture

### Medallion Layers

```
Raw CSVs (sandbox/data/raw/sales/)
         │
         ▼
┌─────────────────────┐
│  BRONZE             │  Raw ingestion — all 525 rows, no transformation
│  Delta Lake         │  Metadata columns added (ingestion_timestamp, source_system)
│  data/bronze/sales  │  Append-only, immutable raw record
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐     ┌──────────────────────┐
│  SILVER             │────▶│  QUARANTINE           │
│  Delta Lake         │     │  25 bad records       │
│  data/silver/sales  │     │  with quarantine      │
│  500 clean rows     │     │  reason column        │
└─────────┬───────────┘     └──────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────┐
│  GOLD                                               │
│  data/gold/by_segment   — Revenue by segment        │
│  data/gold/by_region    — Revenue by region         │
│  data/gold/monthly_trend — Monthly revenue trend    │
└─────────────────────────────────────────────────────┘
```

### Local → Azure Mapping

| Local sandbox | Azure production equivalent |
|---|---|
| `spark.read.csv(RAW_PATH)` | Auto Loader reading from ADLS Gen2 |
| `local[*]` Spark master | Databricks job cluster |
| Delta files on local disk | Delta tables in ADLS Gen2 |
| Manual filter/quarantine | DLT `@dlt.expect_or_drop` expectations |
| `python3 medallion_demo.py` | Databricks Workflow or ADF trigger |
| `.venv` + `pip install` | Databricks cluster libraries |

The pipeline logic, Delta operations, and quality patterns are identical. Only the storage path and compute target change in production.

---

## Repository Structure

```
azure-modern-data-platform/
├── sandbox/
│   ├── generate_test_data.py          # Generates 525-row retail dataset
│   ├── pipelines/
│   │   ├── medallion_demo.py          # Bronze → Silver → Gold pipeline
│   │   └── delta_time_travel_demo.py  # ACID update + VERSION AS OF demo
│   ├── data/                          # Generated at runtime (gitignored)
│   │   ├── raw/sales/                 # Input CSV batch files
│   │   ├── bronze/sales/              # Delta table — raw
│   │   ├── silver/sales/              # Delta table — cleaned
│   │   ├── gold/                      # Delta tables — aggregated
│   │   └── quarantine/sales/          # Delta table — rejected records
│   ├── notebooks/                     # Jupyter notebooks
│   └── config/                        # Grafana, Prometheus config
├── automation/                        # Azure Functions self-healing monitor
├── governance/                        # Unity Catalog setup
├── infrastructure/                    # Terraform IaC for Azure deployment
├── pipelines/                         # ADF pipeline definitions
├── scripts/                           # Deployment scripts
├── .gitignore
└── README.md
```

---

## Tech Stack

| Component | Local sandbox | Azure production |
|---|---|---|
| Compute | PySpark 3.5.0 local[*] | Azure Databricks |
| Storage format | Delta Lake 3.2.0 | Delta Lake on ADLS Gen2 |
| Orchestration | CLI / shell | Azure Data Factory / Databricks Workflows |
| Governance | — | Unity Catalog |
| Quality | Filter + quarantine | Delta Live Tables expectations |
| Monitoring | — | Azure Monitor + Grafana |
| IaC | — | Terraform (see `infrastructure/`) |

---

## Key Data Engineering Concepts Demonstrated

**Idempotency** — Pipeline writes use `mode("overwrite")` on Delta tables. Re-running after a failure produces the same result with no duplicates.

**Data quality as a first-class concern** — Bad records are never silently dropped or passed through. They are isolated to a quarantine table with a documented reason column, making data quality issues auditable and recoverable.

**ACID on a data lake** — Delta Lake's transaction log ensures every write is atomic. A failed mid-write leaves the table in its previous valid state — no corrupt partial writes.

**Time travel for auditability** — Every table operation is versioned. Historical states are queryable without restoring from backup. Critical for compliance, debugging bad loads, and root cause analysis.

**Separation of concerns** — Bronze preserves raw data permanently. Transformation logic lives in Silver and Gold. If a bug is found in Silver logic, raw Bronze data is always available for reprocessing.

---

## License

MIT
