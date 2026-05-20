"""
Delta Lake Time Travel Demo
Run AFTER medallion_demo.py to show versioned history
"""
import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, current_timestamp, lit
from delta import configure_spark_with_delta_pip
from delta.tables import DeltaTable

BASE        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SILVER_PATH = os.path.join(BASE, "data/silver/sales")

builder = (
    SparkSession.builder
    .appName("TimeTravelDemo")
    .master("local[*]")
    .config("spark.sql.extensions",
            "io.delta.sql.DeltaSparkSessionExtension")
    .config("spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog")
    .config("spark.log.level", "WARN")
)
spark = configure_spark_with_delta_pip(builder).getOrCreate()
spark.sparkContext.setLogLevel("WARN")

print("\n═══ DELTA LAKE — TIME TRAVEL DEMO ═══\n")

# ── Read current Silver ───────────────────────────────────────────────────────
silver = spark.read.format("delta").load(SILVER_PATH)
v0_count = silver.count()
print(f"Version 0  →  {v0_count} rows (original pipeline run)")

# ── Simulate a correction: mark Premium Manila customers as VIP ───────────────
dt = DeltaTable.forPath(spark, SILVER_PATH)

dt.update(
    condition = (col("customer_segment") == "Premium") &
                (col("region") == "Metro Manila"),
    set = {
        "customer_segment": lit("VIP"),
        "record_status":    lit("UPDATED")
    }
)

updated_count = spark.read.format("delta").load(SILVER_PATH) \
                     .filter(col("customer_segment") == "VIP").count()

print(f"Update applied  →  {updated_count} Premium Metro Manila customers "
      f"reclassified as VIP\n")

# ── Show full version history ─────────────────────────────────────────────────
print("── Delta Transaction Log History ──")
spark.sql(f"DESCRIBE HISTORY delta.`{SILVER_PATH}`") \
     .select("version", "timestamp", "operation", "operationMetrics") \
     .show(truncate=False)

# ── Time travel: read version 0 (before the update) ──────────────────────────
v0 = spark.read.format("delta").option("versionAsOf", 0).load(SILVER_PATH)
v1 = spark.read.format("delta").load(SILVER_PATH)

print("── VERSION AS OF 0  (before update) ──")
v0.groupBy("customer_segment").count().orderBy("count").show()

print("── VERSION AS OF 1  (after update) ──")
v1.groupBy("customer_segment").count().orderBy("count").show()

print("── Rows changed between v0 and v1 ──")
changed = v0.alias("v0").join(
    v1.alias("v1"), on="sale_id"
).filter(
    col("v0.customer_segment") != col("v1.customer_segment")
).select(
    col("v0.sale_id"),
    col("v0.customer_segment").alias("was"),
    col("v1.customer_segment").alias("now"),
    col("v0.region")
)
changed.show(10, truncate=False)

print(f"Total rows changed: {changed.count()}")
print("\nThis is Delta Lake time travel — any version, any point in time.")
print("In production: use this for audits, rollbacks, and debugging bad loads.\n")

spark.stop()
