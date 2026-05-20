"""
Azure Modern Data Platform — Medallion Architecture Demo
Bronze → Silver → Gold using local PySpark + Delta Lake
Uses generated retail sales data (500 good + 25 bad records)
"""

import os
import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, sum, avg, count, countDistinct, max, min,
    current_timestamp, lit, when, to_date, round as spark_round,
    date_format
)
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType,
    IntegerType, DecimalType
)
from delta import configure_spark_with_delta_pip

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)

# ── paths ────────────────────────────────────────────────────────────────────
BASE        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_PATH    = os.path.join(BASE, "data/raw/sales")
BRONZE_PATH = os.path.join(BASE, "data/bronze/sales")
SILVER_PATH = os.path.join(BASE, "data/silver/sales")
GOLD_SEG    = os.path.join(BASE, "data/gold/by_segment")
GOLD_REGION = os.path.join(BASE, "data/gold/by_region")
GOLD_TREND  = os.path.join(BASE, "data/gold/monthly_trend")
QUARANTINE  = os.path.join(BASE, "data/quarantine/sales")

for p in [BRONZE_PATH, SILVER_PATH, GOLD_SEG, GOLD_REGION, GOLD_TREND, QUARANTINE]:
    os.makedirs(p, exist_ok=True)


# ── spark session ─────────────────────────────────────────────────────────────
def create_spark():
    builder = (
        SparkSession.builder
        .appName("MedallionArchitectureDemo")
        .master("local[*]")
        .config("spark.sql.extensions",
                "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog",
                "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
        .config("spark.driver.memory", "2g")
        # suppress verbose Spark logs
        .config("spark.log.level", "WARN")
    )
    spark = configure_spark_with_delta_pip(builder).getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    log.info("Spark + Delta Lake ready  (local[*])")
    return spark


# ── BRONZE ────────────────────────────────────────────────────────────────────
def bronze(spark):
    log.info("── BRONZE  reading raw CSVs ──")

    raw = (
        spark.read
        .option("header", "true")
        .option("inferSchema", "true")
        .csv(RAW_PATH)
    )

    bronze_df = (
        raw
        .withColumn("ingestion_timestamp", current_timestamp())
        .withColumn("source_system",       lit("pos_system_v2"))
        .withColumn("layer",               lit("bronze"))
    )

    bronze_df.write.format("delta").mode("overwrite").save(BRONZE_PATH)

    total = bronze_df.count()
    log.info(f"Bronze  {total} rows written → {BRONZE_PATH}")

    print("\n╔══════════════════════════════════╗")
    print("║  BRONZE — raw ingestion sample   ║")
    print("╚══════════════════════════════════╝")
    bronze_df.select(
        "sale_id","sale_date","customer_id","customer_segment",
        "sale_amount","region","_bad_reason"
    ).show(8, truncate=False)

    return total


# ── SILVER ────────────────────────────────────────────────────────────────────
def silver(spark):
    log.info("── SILVER  apply quality rules ──")

    bronze_df = spark.read.format("delta").load(BRONZE_PATH)

    # rows that PASS quality checks
    silver_df = (
        bronze_df
        .filter(col("sale_amount") > 0)
        .filter(col("customer_id").isNotNull())
        .withColumn("sale_amount",          col("sale_amount").cast(DecimalType(12, 2)))
        .withColumn("sale_date",            to_date(col("sale_date"), "yyyy-MM-dd"))
        .withColumn("processed_timestamp",  current_timestamp())
        .withColumn("record_status",        lit("VALID"))
        .drop("_bad_reason")
    )

    # rows that FAIL — quarantined
    quarantine_df = (
        bronze_df
        .filter(
            (col("sale_amount") <= 0) | col("customer_id").isNull()
        )
        .withColumn(
            "quarantine_reason",
            when(col("sale_amount") <= 0,    "negative_sale_amount")
            .when(col("customer_id").isNull(), "null_customer_id")
            .otherwise("unknown")
        )
        .withColumn("quarantine_timestamp", current_timestamp())
    )

    silver_df.write.format("delta").mode("overwrite").save(SILVER_PATH)
    quarantine_df.write.format("delta").mode("overwrite").save(QUARANTINE)

    valid_count = silver_df.count()
    bad_count   = quarantine_df.count()
    quality_pct = round(valid_count / (valid_count + bad_count) * 100, 1)

    print("\n╔══════════════════════════════════════════════════╗")
    print("║  SILVER — quality enforcement results            ║")
    print("╚══════════════════════════════════════════════════╝")
    print(f"  ✓ Valid records passed to Silver : {valid_count}")
    print(f"  ✗ Bad records sent to Quarantine : {bad_count}")
    print(f"  Data quality rate                : {quality_pct}%\n")

    print("  Quarantined records breakdown:")
    quarantine_df.groupBy("quarantine_reason").count().show(truncate=False)

    return valid_count, bad_count


# ── GOLD ──────────────────────────────────────────────────────────────────────
def gold(spark):
    log.info("── GOLD  build business aggregates ──")

    silver_df = spark.read.format("delta").load(SILVER_PATH)

    # ── 1. Revenue by customer segment ───────────────────────────────────────
    by_segment = (
        silver_df
        .groupBy("customer_segment")
        .agg(
            spark_round(sum("sale_amount"),         2).alias("total_revenue"),
            spark_round(avg("sale_amount"),         2).alias("avg_order_value"),
            count("sale_id").alias("total_orders"),
            countDistinct("customer_id").alias("unique_customers")
        )
        .withColumn(
            "revenue_per_customer",
            spark_round(col("total_revenue") / col("unique_customers"), 2)
        )
        .orderBy(col("total_revenue").desc())
    )

    by_segment.write.format("delta").mode("overwrite").save(GOLD_SEG)

    print("\n╔══════════════════════════════════════════════════════════════╗")
    print("║  GOLD — Revenue by Customer Segment                         ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    by_segment.show(truncate=False)

    # ── 2. Revenue by region ─────────────────────────────────────────────────
    by_region = (
        silver_df
        .groupBy("region")
        .agg(
            spark_round(sum("sale_amount"),   2).alias("total_revenue"),
            count("sale_id").alias("total_orders"),
            countDistinct("customer_id").alias("unique_customers"),
            spark_round(avg("sale_amount"),   2).alias("avg_order_value")
        )
        .orderBy(col("total_revenue").desc())
    )

    by_region.write.format("delta").mode("overwrite").save(GOLD_REGION)

    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  GOLD — Revenue by Region                                    ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    by_region.show(truncate=False)

    # ── 3. Monthly revenue trend ─────────────────────────────────────────────
    monthly = (
        silver_df
        .withColumn("month", date_format("sale_date", "yyyy-MM"))
        .groupBy("month")
        .agg(
            spark_round(sum("sale_amount"), 2).alias("monthly_revenue"),
            count("sale_id").alias("orders"),
            countDistinct("customer_id").alias("unique_customers")
        )
        .orderBy("month")
    )

    monthly.write.format("delta").mode("overwrite").save(GOLD_TREND)

    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  GOLD — Monthly Revenue Trend (Jan–May 2025)                 ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    monthly.show(truncate=False)


# ── DELTA FEATURES ────────────────────────────────────────────────────────────
def delta_features(spark):
    print("\n╔══════════════════════════════════════════════════════════════╗")
    print("║  DELTA LAKE FEATURES — Time Travel & History                 ║")
    print("╚══════════════════════════════════════════════════════════════╝")

    # Table history
    spark.sql(f"DESCRIBE HISTORY delta.`{SILVER_PATH}`") \
         .select("version","timestamp","operation","operationMetrics") \
         .show(5, truncate=False)

    # Time travel — read version 0 (original write)
    v0_count = (
        spark.read.format("delta")
        .option("versionAsOf", 0)
        .load(SILVER_PATH)
        .count()
    )
    print(f"  Time Travel  VERSION AS OF 0 → {v0_count} rows  (same as current, only 1 write so far)")
    print("  In production: VERSION AS OF lets you query any historical snapshot.")


# ── SUMMARY ───────────────────────────────────────────────────────────────────
def summary(bronze_total, silver_valid, silver_bad):
    quality_pct = round(silver_valid / bronze_total * 100, 1)
    print("\n" + "═" * 62)
    print("  MEDALLION PIPELINE — RUN SUMMARY")
    print("═" * 62)
    print(f"  Bronze  (raw ingested)    : {bronze_total} rows")
    print(f"  Silver  (passed quality)  : {silver_valid} rows")
    print(f"  Quarantine (rejected)     : {silver_bad} rows")
    print(f"  Data quality rate         : {quality_pct}%")
    print(f"  Gold tables written       : by_segment, by_region, monthly_trend")
    print("═" * 62)
    print("\n  Delta Lake paths:")
    print(f"    Bronze    → {BRONZE_PATH}")
    print(f"    Silver    → {SILVER_PATH}")
    print(f"    Gold      → {os.path.dirname(GOLD_SEG)}")
    print(f"    Quarantine→ {QUARANTINE}")
    print("\n  Done.\n")


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print("═" * 62)
    print("  Azure Modern Data Platform — Medallion Architecture Demo")
    print("  Local Sandbox  |  PySpark + Delta Lake  |  local[*]")
    print("═" * 62 + "\n")

    spark = create_spark()

    bronze_total            = bronze(spark)
    silver_valid, silver_bad = silver(spark)
    gold(spark)
    delta_features(spark)
    summary(bronze_total, silver_valid, silver_bad)

    spark.stop()


if __name__ == "__main__":
    main()
