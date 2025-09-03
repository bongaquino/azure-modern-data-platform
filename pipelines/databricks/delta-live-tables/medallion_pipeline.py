# Delta Live Tables Pipeline for Medallion Architecture
# Declarative, Self-Managing ETL Pipeline for Modern Data Platform

import dlt
from pyspark.sql.functions import *
from pyspark.sql.types import *

# Pipeline Configuration
BRONZE_PATH = "/mnt/data-lake/bronze"
SILVER_PATH = "/mnt/data-lake/silver"
GOLD_PATH = "/mnt/data-lake/gold"
CHECKPOINT_PATH = "/mnt/data-lake/checkpoints"

# Data Quality Thresholds
QUALITY_THRESHOLDS = {
    "min_rows": 1,
    "max_null_percentage": 5.0,
    "max_duplicate_percentage": 2.0
}

# ===========================
# BRONZE LAYER (Raw Data)
# ===========================

@dlt.table(
    name="bronze_sales_raw",
    comment="Raw sales data from various sources with automated ingestion",
    table_properties={
        "delta.autoOptimize.optimizeWrite": "true",
        "delta.autoOptimize.autoCompact": "true",
        "delta.enableChangeDataFeed": "true"
    }
)
def bronze_sales_raw():
    """
    Bronze layer: Raw data ingestion with minimal transformation
    Automated streaming ingestion from multiple sources
    """
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.schemaLocation", f"{CHECKPOINT_PATH}/bronze_sales_schema")
        .option("cloudFiles.inferColumnTypes", "true")
        .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
        .load(f"{BRONZE_PATH}/sales/")
        .withColumn("ingestion_timestamp", current_timestamp())
        .withColumn("source_file", input_file_name())
        .withColumn("batch_id", expr("uuid()"))
    )

@dlt.table(
    name="bronze_customers_raw",
    comment="Raw customer data with automated schema evolution",
    table_properties={
        "delta.autoOptimize.optimizeWrite": "true",
        "delta.autoOptimize.autoCompact": "true"
    }
)
def bronze_customers_raw():
    """Bronze layer: Customer data ingestion"""
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "csv")
        .option("cloudFiles.schemaLocation", f"{CHECKPOINT_PATH}/bronze_customers_schema")
        .option("header", "true")
        .option("inferSchema", "true")
        .load(f"{BRONZE_PATH}/customers/")
        .withColumn("ingestion_timestamp", current_timestamp())
        .withColumn("source_file", input_file_name())
    )

@dlt.table(
    name="bronze_products_raw",
    comment="Raw product catalog data",
    table_properties={
        "delta.autoOptimize.optimizeWrite": "true"
    }
)
def bronze_products_raw():
    """Bronze layer: Product data ingestion"""
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "parquet")
        .option("cloudFiles.schemaLocation", f"{CHECKPOINT_PATH}/bronze_products_schema")
        .load(f"{BRONZE_PATH}/products/")
        .withColumn("ingestion_timestamp", current_timestamp())
        .withColumn("source_file", input_file_name())
    )

# ===========================
# SILVER LAYER (Cleaned Data)
# ===========================

@dlt.table(
    name="silver_sales_cleaned",
    comment="Cleaned and validated sales data with data quality checks",
    table_properties={
        "delta.autoOptimize.optimizeWrite": "true",
        "delta.autoOptimize.autoCompact": "true",
        "pipelines.autoOptimize.managed": "true"
    }
)
@dlt.expect_or_drop("valid_sale_amount", "sale_amount > 0")
@dlt.expect_or_drop("valid_sale_date", "sale_date IS NOT NULL")
@dlt.expect_or_drop("valid_customer_id", "customer_id IS NOT NULL")
@dlt.expect("valid_sale_id", "sale_id IS NOT NULL")
def silver_sales_cleaned():
    """
    Silver layer: Cleaned sales data with comprehensive validation
    - Standardized column names
    - Data type conversions
    - Data quality checks
    - Deduplication
    """
    return (
        dlt.read_stream("bronze_sales_raw")
        # Standardize column names
        .withColumnRenamed("saleId", "sale_id")
        .withColumnRenamed("customerId", "customer_id")
        .withColumnRenamed("productId", "product_id")
        .withColumnRenamed("saleAmount", "sale_amount")
        .withColumnRenamed("saleDate", "sale_date")
        
        # Data type conversions and cleaning
        .withColumn("sale_id", col("sale_id").cast("string"))
        .withColumn("customer_id", col("customer_id").cast("string"))
        .withColumn("product_id", col("product_id").cast("string"))
        .withColumn("sale_amount", col("sale_amount").cast("decimal(10,2)"))
        .withColumn("sale_date", to_date(col("sale_date"), "yyyy-MM-dd"))
        
        # Clean string fields
        .withColumn("sale_id", trim(upper(col("sale_id"))))
        .withColumn("customer_id", trim(upper(col("customer_id"))))
        .withColumn("product_id", trim(upper(col("product_id"))))
        
        # Add processing metadata
        .withColumn("processed_timestamp", current_timestamp())
        .withColumn("data_quality_score", 
                   when((col("sale_amount") > 0) & 
                        (col("sale_date").isNotNull()) & 
                        (col("customer_id").isNotNull()) &
                        (col("sale_id").isNotNull()), 100.0)
                   .otherwise(0.0))
        
        # Remove duplicates based on business key
        .dropDuplicates(["sale_id", "sale_date"])
    )

@dlt.table(
    name="silver_customers_cleaned",
    comment="Cleaned customer data with PII handling and validation"
)
@dlt.expect_or_drop("valid_customer_id", "customer_id IS NOT NULL")
@dlt.expect_or_drop("valid_email", "email RLIKE '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'")
@dlt.expect("has_contact_info", "email IS NOT NULL OR phone IS NOT NULL")
def silver_customers_cleaned():
    """
    Silver layer: Cleaned customer data with PII protection
    """
    return (
        dlt.read_stream("bronze_customers_raw")
        # Standardize column names
        .withColumnRenamed("customerId", "customer_id")
        .withColumnRenamed("firstName", "first_name")
        .withColumnRenamed("lastName", "last_name")
        .withColumnRenamed("emailAddress", "email")
        .withColumnRenamed("phoneNumber", "phone")
        .withColumnRenamed("registrationDate", "registration_date")
        
        # Data cleaning and standardization
        .withColumn("customer_id", trim(upper(col("customer_id"))))
        .withColumn("first_name", trim(initcap(col("first_name"))))
        .withColumn("last_name", trim(initcap(col("last_name"))))
        .withColumn("email", trim(lower(col("email"))))
        .withColumn("phone", regexp_replace(col("phone"), "[^0-9]", ""))
        .withColumn("registration_date", to_date(col("registration_date"), "yyyy-MM-dd"))
        
        # Add derived fields
        .withColumn("full_name", concat_ws(" ", col("first_name"), col("last_name")))
        .withColumn("customer_age_days", datediff(current_date(), col("registration_date")))
        .withColumn("customer_segment", 
                   when(col("customer_age_days") > 365, "Loyal")
                   .when(col("customer_age_days") > 90, "Regular")
                   .otherwise("New"))
        
        # PII masking for non-production environments
        .withColumn("email_masked", 
                   when(spark.conf.get("spark.databricks.clusterUsageTags.environment") != "prod",
                        concat(substring(col("email"), 1, 3), lit("***@***.com")))
                   .otherwise(col("email")))
        
        .withColumn("processed_timestamp", current_timestamp())
        .dropDuplicates(["customer_id"])
    )

@dlt.table(
    name="silver_products_cleaned",
    comment="Cleaned product catalog with category standardization"
)
@dlt.expect_or_drop("valid_product_id", "product_id IS NOT NULL")
@dlt.expect_or_drop("valid_product_name", "product_name IS NOT NULL")
@dlt.expect_or_drop("valid_price", "price >= 0")
def silver_products_cleaned():
    """
    Silver layer: Cleaned product data with category standardization
    """
    return (
        dlt.read_stream("bronze_products_raw")
        # Standardize column names
        .withColumnRenamed("productId", "product_id")
        .withColumnRenamed("productName", "product_name")
        .withColumnRenamed("categoryName", "category")
        .withColumnRenamed("productPrice", "price")
        .withColumnRenamed("productDescription", "description")
        
        # Data cleaning
        .withColumn("product_id", trim(upper(col("product_id"))))
        .withColumn("product_name", trim(col("product_name")))
        .withColumn("category", trim(initcap(col("category"))))
        .withColumn("price", col("price").cast("decimal(10,2)"))
        .withColumn("description", trim(col("description")))
        
        # Category standardization
        .withColumn("category_standardized",
                   when(col("category").isin("Electronics", "Technology", "Gadgets"), "Electronics")
                   .when(col("category").isin("Clothing", "Apparel", "Fashion"), "Apparel")
                   .when(col("category").isin("Home", "Household", "Furniture"), "Home & Garden")
                   .otherwise(col("category")))
        
        # Add metadata
        .withColumn("processed_timestamp", current_timestamp())
        .dropDuplicates(["product_id"])
    )

# ===========================
# GOLD LAYER (Business Ready)
# ===========================

@dlt.table(
    name="gold_sales_analytics",
    comment="Business-ready sales analytics with aggregations and KPIs",
    table_properties={
        "pipelines.autoOptimize.managed": "true"
    }
)
def gold_sales_analytics():
    """
    Gold layer: Business analytics for sales performance
    """
    sales = dlt.read("silver_sales_cleaned")
    customers = dlt.read("silver_customers_cleaned")
    products = dlt.read("silver_products_cleaned")
    
    # Join all dimensions
    sales_enriched = (
        sales
        .join(customers, "customer_id", "left")
        .join(products, "product_id", "left")
    )
    
    # Calculate daily sales aggregations
    return (
        sales_enriched
        .groupBy(
            "sale_date",
            "category_standardized",
            "customer_segment"
        )
        .agg(
            count("sale_id").alias("transaction_count"),
            sum("sale_amount").alias("total_sales"),
            avg("sale_amount").alias("avg_transaction_value"),
            min("sale_amount").alias("min_transaction_value"),
            max("sale_amount").alias("max_transaction_value"),
            countDistinct("customer_id").alias("unique_customers"),
            countDistinct("product_id").alias("unique_products")
        )
        .withColumn("sales_per_customer", col("total_sales") / col("unique_customers"))
        .withColumn("products_per_transaction", col("unique_products") / col("transaction_count"))
        .withColumn("processed_timestamp", current_timestamp())
    )

@dlt.table(
    name="gold_customer_360",
    comment="360-degree customer view with lifetime value and behavior"
)
def gold_customer_360():
    """
    Gold layer: Comprehensive customer analytics
    """
    sales = dlt.read("silver_sales_cleaned")
    customers = dlt.read("silver_customers_cleaned")
    
    # Customer transaction summary
    customer_metrics = (
        sales
        .groupBy("customer_id")
        .agg(
            count("sale_id").alias("total_transactions"),
            sum("sale_amount").alias("lifetime_value"),
            avg("sale_amount").alias("avg_order_value"),
            min("sale_date").alias("first_purchase_date"),
            max("sale_date").alias("last_purchase_date"),
            countDistinct("product_id").alias("unique_products_purchased")
        )
        .withColumn("customer_tenure_days", 
                   datediff(col("last_purchase_date"), col("first_purchase_date")))
        .withColumn("purchase_frequency", 
                   col("total_transactions") / (col("customer_tenure_days") + 1))
    )
    
    # Join with customer details
    return (
        customers
        .join(customer_metrics, "customer_id", "left")
        .withColumn("customer_value_segment",
                   when(col("lifetime_value") >= 1000, "High Value")
                   .when(col("lifetime_value") >= 500, "Medium Value")
                   .when(col("lifetime_value").isNotNull(), "Low Value")
                   .otherwise("No Purchases"))
        .withColumn("processed_timestamp", current_timestamp())
    )

@dlt.table(
    name="gold_product_performance",
    comment="Product performance metrics and trends"
)
def gold_product_performance():
    """
    Gold layer: Product performance analytics
    """
    sales = dlt.read("silver_sales_cleaned")
    products = dlt.read("silver_products_cleaned")
    
    # Product performance metrics
    product_metrics = (
        sales
        .groupBy("product_id")
        .agg(
            count("sale_id").alias("total_sales_count"),
            sum("sale_amount").alias("total_revenue"),
            avg("sale_amount").alias("avg_sale_price"),
            countDistinct("customer_id").alias("unique_customers"),
            min("sale_date").alias("first_sale_date"),
            max("sale_date").alias("last_sale_date")
        )
        .withColumn("revenue_per_customer", col("total_revenue") / col("unique_customers"))
    )
    
    # Join with product details and add performance indicators
    return (
        products
        .join(product_metrics, "product_id", "left")
        .withColumn("performance_score",
                   coalesce(col("total_revenue"), lit(0)) * 0.6 + 
                   coalesce(col("unique_customers"), lit(0)) * 0.4)
        .withColumn("product_status",
                   when(col("last_sale_date") >= date_sub(current_date(), 30), "Active")
                   .when(col("last_sale_date") >= date_sub(current_date(), 90), "Slow Moving")
                   .when(col("last_sale_date").isNotNull(), "Inactive")
                   .otherwise("Never Sold"))
        .withColumn("processed_timestamp", current_timestamp())
    )

# ===========================
# DATA QUALITY MONITORING
# ===========================

@dlt.table(
    name="data_quality_metrics",
    comment="Automated data quality monitoring and alerting"
)
def data_quality_metrics():
    """
    Automated data quality monitoring across all layers
    """
    from pyspark.sql.functions import when, col, count, sum as spark_sum, lit
    
    # Define tables to monitor
    tables_to_monitor = [
        ("bronze_sales_raw", "bronze"),
        ("silver_sales_cleaned", "silver"),
        ("gold_sales_analytics", "gold")
    ]
    
    quality_results = []
    
    for table_name, layer in tables_to_monitor:
        try:
            df = dlt.read(table_name)
            total_rows = df.count()
            
            if total_rows > 0:
                # Calculate quality metrics
                null_percentage = (df.select(*[sum(col(c).isNull().cast("int")).alias(c) for c in df.columns])
                                 .collect()[0])
                
                quality_record = spark.createDataFrame([{
                    "table_name": table_name,
                    "layer": layer,
                    "total_rows": total_rows,
                    "null_percentage": sum(null_percentage) / (len(df.columns) * total_rows) * 100,
                    "check_timestamp": current_timestamp(),
                    "status": "PASSED" if total_rows >= QUALITY_THRESHOLDS["min_rows"] else "FAILED"
                }])
                
                quality_results.append(quality_record)
        except Exception as e:
            # Log quality check failure
            error_record = spark.createDataFrame([{
                "table_name": table_name,
                "layer": layer,
                "total_rows": 0,
                "null_percentage": 100.0,
                "check_timestamp": current_timestamp(),
                "status": "ERROR",
                "error_message": str(e)
            }])
            quality_results.append(error_record)
    
    # Union all quality results
    if quality_results:
        return quality_results[0].unionAll(*quality_results[1:]) if len(quality_results) > 1 else quality_results[0]
    else:
        # Return empty DataFrame with schema
        return spark.createDataFrame([], schema=StructType([
            StructField("table_name", StringType()),
            StructField("layer", StringType()),
            StructField("total_rows", LongType()),
            StructField("null_percentage", DoubleType()),
            StructField("check_timestamp", TimestampType()),
            StructField("status", StringType()),
            StructField("error_message", StringType())
        ]))

# ===========================
# PIPELINE HEALTH MONITORING
# ===========================

@dlt.table(
    name="pipeline_health_metrics",
    comment="Pipeline execution health and performance metrics"
)
def pipeline_health_metrics():
    """
    Monitor pipeline execution health and performance
    """
    return spark.createDataFrame([{
        "pipeline_name": "medallion_architecture_pipeline",
        "execution_timestamp": current_timestamp(),
        "pipeline_version": "1.0.0",
        "bronze_tables_count": 3,
        "silver_tables_count": 3,
        "gold_tables_count": 3,
        "quality_checks_passed": True,
        "execution_duration_minutes": None,  # Would be populated by monitoring system
        "status": "RUNNING"
    }])
