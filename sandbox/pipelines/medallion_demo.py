# Medallion Architecture Demo - Local Sandbox
# Demonstrates Bronze → Silver → Gold data pipeline using local Spark

import os
import sys
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_spark_session():
    """Create Spark session with Delta Lake support"""
    try:
        from pyspark.sql import SparkSession
        from pyspark.sql.functions import *
        from pyspark.sql.types import *
        
        spark = SparkSession.builder \
            .appName("MedallionArchitectureDemo") \
            .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
            .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
            .config("spark.master", "local[*]") \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
            .getOrCreate()
        
        logger.info("✅ Spark session created successfully")
        return spark
        
    except ImportError as e:
        logger.error(f"Failed to import required libraries: {e}")
        logger.info("Installing required packages...")
        os.system("pip install pyspark==3.5.0 delta-spark==2.4.0")
        return create_spark_session()

def generate_sample_data(spark):
    """Generate sample data for demonstration"""
    logger.info("🔧 Generating sample data...")
    
    # Sample sales transactions
    sample_data = [
        ("TXN001", "CUST001", "PROD001", 299.99, "2024-01-15", "2024-01-15 10:30:00", "New York", "Credit Card"),
        ("TXN002", "CUST002", "PROD002", 149.99, "2024-01-15", "2024-01-15 11:45:00", "California", "Debit Card"),
        ("TXN003", "CUST001", "PROD003", 599.99, "2024-01-16", "2024-01-16 09:15:00", "New York", "Credit Card"),
        ("TXN004", "CUST003", "PROD001", 299.99, "2024-01-16", "2024-01-16 14:20:00", "Texas", "Cash"),
        ("TXN005", "CUST002", "PROD004", 89.99, "2024-01-17", "2024-01-17 16:00:00", "California", "Credit Card"),
        ("TXN006", "CUST004", "PROD001", 299.99, "2024-01-17", "2024-01-17 18:30:00", "Florida", "Credit Card"),
        ("TXN007", "CUST001", "PROD005", 199.99, "2024-01-18", "2024-01-18 12:15:00", "New York", "Debit Card"),
        ("TXN008", "CUST005", "PROD002", 149.99, "2024-01-18", "2024-01-18 15:45:00", "Illinois", "Cash"),
        ("TXN009", "CUST003", "PROD006", 449.99, "2024-01-19", "2024-01-19 11:00:00", "Texas", "Credit Card"),
        ("TXN010", "CUST002", "PROD001", 299.99, "2024-01-19", "2024-01-19 14:30:00", "California", "Credit Card")
    ]
    
    schema = StructType([
        StructField("transaction_id", StringType(), True),
        StructField("customer_id", StringType(), True),
        StructField("product_id", StringType(), True),
        StructField("sale_amount", DoubleType(), True),
        StructField("sale_date", StringType(), True),
        StructField("sale_timestamp", StringType(), True),
        StructField("store_location", StringType(), True),
        StructField("payment_method", StringType(), True)
    ])
    
    from pyspark.sql.types import StructType, StructField, StringType, DoubleType
    from pyspark.sql.functions import col, current_timestamp, lit
    
    # Create DataFrame
    raw_df = spark.createDataFrame(sample_data, schema)
    
    # Add some data quality issues for demonstration
    # Add null values and invalid data
    quality_issues_data = [
        ("TXN011", None, "PROD001", 299.99, "2024-01-20", "2024-01-20 10:00:00", "Nevada", "Credit Card"),  # Missing customer_id
        ("TXN012", "CUST006", "PROD002", -50.00, "2024-01-20", "2024-01-20 11:00:00", "Oregon", "Debit Card"),  # Negative amount
        ("TXN013", "CUST007", "PROD003", None, "2024-01-20", "2024-01-20 12:00:00", "Washington", "Cash"),  # Missing amount
    ]
    
    quality_df = spark.createDataFrame(quality_issues_data, schema)
    
    # Combine clean and problematic data
    combined_df = raw_df.union(quality_df)
    
    logger.info(f"✅ Generated {combined_df.count()} sample records")
    return combined_df

def bronze_layer_processing(spark, raw_df):
    """Bronze Layer: Raw data ingestion with minimal processing"""
    logger.info("🥉 Processing Bronze Layer...")
    
    from pyspark.sql.functions import current_timestamp, lit, input_file_name
    
    # Bronze layer: Add metadata columns
    bronze_df = raw_df \
        .withColumn("ingestion_timestamp", current_timestamp()) \
        .withColumn("source_system", lit("sample_data_generator")) \
        .withColumn("batch_id", lit("BATCH_001")) \
        .withColumn("source_file", lit("sample_data.csv"))
    
    # Create bronze directory if it doesn't exist
    bronze_path = "data/bronze/sales"
    os.makedirs(bronze_path, exist_ok=True)
    
    # Write to bronze layer (Parquet for simplicity in local mode)
    bronze_df.coalesce(1).write \
        .mode("overwrite") \
        .parquet(bronze_path)
    
    logger.info(f"✅ Bronze layer created with {bronze_df.count()} records")
    logger.info(f"   Saved to: {bronze_path}")
    
    # Show sample data
    print("\n📊 Bronze Layer Sample:")
    bronze_df.show(5, truncate=False)
    
    return bronze_df

def silver_layer_processing(spark):
    """Silver Layer: Data cleaning and validation"""
    logger.info("🥈 Processing Silver Layer...")
    
    from pyspark.sql.functions import col, when, isnan, isnull, current_timestamp, lit
    
    # Read from bronze layer
    bronze_path = "data/bronze/sales"
    bronze_df = spark.read.parquet(bronze_path)
    
    # Data cleaning and validation rules
    silver_df = bronze_df \
        .filter(col("transaction_id").isNotNull()) \
        .filter(col("customer_id").isNotNull()) \
        .filter(col("sale_amount").isNotNull()) \
        .filter(col("sale_amount") > 0) \
        .withColumn("sale_amount", col("sale_amount").cast("decimal(10,2)")) \
        .withColumn("sale_date", to_date(col("sale_date"), "yyyy-MM-dd")) \
        .withColumn("sale_timestamp", to_timestamp(col("sale_timestamp"), "yyyy-MM-dd HH:mm:ss")) \
        .withColumn("processed_timestamp", current_timestamp()) \
        .withColumn("data_quality_score", lit(100.0)) \
        .withColumn("record_status", lit("VALID"))
    
    # Identify and handle quarantine records
    quarantine_df = bronze_df \
        .filter(
            col("transaction_id").isNull() | 
            col("customer_id").isNull() | 
            col("sale_amount").isNull() | 
            (col("sale_amount") <= 0)
        ) \
        .withColumn("quarantine_reason", 
                   when(col("transaction_id").isNull(), "Missing transaction ID")
                   .when(col("customer_id").isNull(), "Missing customer ID")
                   .when(col("sale_amount").isNull(), "Missing sale amount")
                   .when(col("sale_amount") <= 0, "Invalid sale amount")
                   .otherwise("Unknown validation error")) \
        .withColumn("quarantine_timestamp", current_timestamp())
    
    # Create silver and quarantine directories
    silver_path = "data/silver/sales"
    quarantine_path = "data/quarantine/sales"
    os.makedirs(silver_path, exist_ok=True)
    os.makedirs(quarantine_path, exist_ok=True)
    
    # Write to silver layer
    silver_df.coalesce(1).write \
        .mode("overwrite") \
        .parquet(silver_path)
    
    # Write quarantine records
    if quarantine_df.count() > 0:
        quarantine_df.coalesce(1).write \
            .mode("overwrite") \
            .parquet(quarantine_path)
    
    logger.info(f"✅ Silver layer created with {silver_df.count()} valid records")
    logger.info(f"   Quarantined {quarantine_df.count()} invalid records")
    logger.info(f"   Saved to: {silver_path}")
    
    # Show sample data
    print("\n📊 Silver Layer Sample:")
    silver_df.show(5, truncate=False)
    
    if quarantine_df.count() > 0:
        print("\n⚠️ Quarantined Records:")
        quarantine_df.select("transaction_id", "customer_id", "sale_amount", "quarantine_reason").show(truncate=False)
    
    return silver_df

def gold_layer_processing(spark):
    """Gold Layer: Business aggregations and analytics"""
    logger.info("🥇 Processing Gold Layer...")
    
    from pyspark.sql.functions import col, sum, avg, count, countDistinct, max, min, current_timestamp
    
    # Read from silver layer
    silver_path = "data/silver/sales"
    silver_df = spark.read.parquet(silver_path)
    
    # Business aggregation 1: Daily sales summary
    daily_sales = silver_df \
        .groupBy("sale_date", "store_location") \
        .agg(
            count("transaction_id").alias("transaction_count"),
            sum("sale_amount").alias("total_sales"),
            avg("sale_amount").alias("avg_transaction_value"),
            max("sale_amount").alias("max_transaction_value"),
            min("sale_amount").alias("min_transaction_value"),
            countDistinct("customer_id").alias("unique_customers"),
            countDistinct("product_id").alias("unique_products")
        ) \
        .withColumn("sales_per_customer", col("total_sales") / col("unique_customers")) \
        .withColumn("processed_timestamp", current_timestamp()) \
        .orderBy("sale_date", "store_location")
    
    # Business aggregation 2: Customer analytics
    customer_analytics = silver_df \
        .groupBy("customer_id") \
        .agg(
            count("transaction_id").alias("total_transactions"),
            sum("sale_amount").alias("lifetime_value"),
            avg("sale_amount").alias("avg_order_value"),
            max("sale_date").alias("last_purchase_date"),
            min("sale_date").alias("first_purchase_date"),
            countDistinct("product_id").alias("unique_products_purchased"),
            countDistinct("store_location").alias("unique_locations_visited")
        ) \
        .withColumn("customer_tenure_days", 
                   datediff(col("last_purchase_date"), col("first_purchase_date"))) \
        .withColumn("customer_value_segment",
                   when(col("lifetime_value") >= 1000, "High Value")
                   .when(col("lifetime_value") >= 500, "Medium Value")
                   .otherwise("Low Value")) \
        .withColumn("processed_timestamp", current_timestamp()) \
        .orderBy(col("lifetime_value").desc())
    
    # Business aggregation 3: Product performance
    product_performance = silver_df \
        .groupBy("product_id") \
        .agg(
            count("transaction_id").alias("total_sales_count"),
            sum("sale_amount").alias("total_revenue"),
            avg("sale_amount").alias("avg_sale_price"),
            countDistinct("customer_id").alias("unique_customers"),
            countDistinct("store_location").alias("unique_locations")
        ) \
        .withColumn("revenue_per_customer", col("total_revenue") / col("unique_customers")) \
        .withColumn("market_penetration", col("unique_locations") / lit(5.0))  # Assuming 5 total locations \
        .withColumn("processed_timestamp", current_timestamp()) \
        .orderBy(col("total_revenue").desc())
    
    # Create gold directories
    gold_daily_path = "data/gold/daily_sales"
    gold_customer_path = "data/gold/customer_analytics"
    gold_product_path = "data/gold/product_performance"
    
    os.makedirs(gold_daily_path, exist_ok=True)
    os.makedirs(gold_customer_path, exist_ok=True)
    os.makedirs(gold_product_path, exist_ok=True)
    
    # Write to gold layer
    daily_sales.coalesce(1).write.mode("overwrite").parquet(gold_daily_path)
    customer_analytics.coalesce(1).write.mode("overwrite").parquet(gold_customer_path)
    product_performance.coalesce(1).write.mode("overwrite").parquet(gold_product_path)
    
    logger.info(f"✅ Gold layer created with {daily_sales.count()} daily summaries")
    logger.info(f"   Customer analytics: {customer_analytics.count()} customers")
    logger.info(f"   Product performance: {product_performance.count()} products")
    
    # Show sample data
    print("\n📊 Gold Layer - Daily Sales Summary:")
    daily_sales.show(10, truncate=False)
    
    print("\n📊 Gold Layer - Customer Analytics:")
    customer_analytics.show(5, truncate=False)
    
    print("\n📊 Gold Layer - Product Performance:")
    product_performance.show(5, truncate=False)
    
    return daily_sales, customer_analytics, product_performance

def demonstrate_data_quality_monitoring(spark):
    """Demonstrate data quality monitoring capabilities"""
    logger.info("🔍 Demonstrating Data Quality Monitoring...")
    
    # Read data from different layers
    bronze_df = spark.read.parquet("data/bronze/sales")
    silver_df = spark.read.parquet("data/silver/sales")
    
    # Calculate data quality metrics
    total_bronze_records = bronze_df.count()
    total_silver_records = silver_df.count()
    quarantined_records = total_bronze_records - total_silver_records
    data_quality_rate = (total_silver_records / total_bronze_records) * 100
    
    print(f"\n📈 Data Quality Metrics:")
    print(f"   Total Raw Records (Bronze): {total_bronze_records}")
    print(f"   Valid Records (Silver): {total_silver_records}")
    print(f"   Quarantined Records: {quarantined_records}")
    print(f"   Data Quality Rate: {data_quality_rate:.2f}%")
    
    # Demonstrate data lineage
    print(f"\n🔗 Data Lineage Summary:")
    print(f"   Bronze → Silver: {total_bronze_records} → {total_silver_records} records")
    print(f"   Data Loss: {quarantined_records} records ({((quarantined_records/total_bronze_records)*100):.2f}%)")
    
    logger.info("✅ Data quality monitoring complete")

def main():
    """Main function to run the medallion architecture demo"""
    print("=" * 80)
    print("🚀 Azure Modern Data Platform - Medallion Architecture Demo")
    print("   Local Sandbox Environment")
    print("=" * 80)
    
    try:
        # Create Spark session
        spark = create_spark_session()
        
        # Generate sample data
        raw_data = generate_sample_data(spark)
        
        # Process through medallion layers
        bronze_df = bronze_layer_processing(spark, raw_data)
        silver_df = silver_layer_processing(spark)
        gold_results = gold_layer_processing(spark)
        
        # Demonstrate data quality monitoring
        demonstrate_data_quality_monitoring(spark)
        
        print("\n" + "=" * 80)
        print("✅ Medallion Architecture Demo Complete!")
        print("=" * 80)
        print("\nData Location Summary:")
        print("  • Bronze Layer: data/bronze/sales")
        print("  • Silver Layer: data/silver/sales")
        print("  • Gold Layer: data/gold/daily_sales, customer_analytics, product_performance")
        print("  • Quarantine: data/quarantine/sales")
        print("\nNext Steps:")
        print("  1. Explore the generated data files")
        print("  2. Run the Jupyter notebook for interactive analysis")
        print("  3. Set up monitoring dashboards in Grafana")
        print("  4. Experiment with Delta Lake features")
        
    except Exception as e:
        logger.error(f"Demo failed: {str(e)}")
        raise
    finally:
        spark.stop()

if __name__ == "__main__":
    main()
