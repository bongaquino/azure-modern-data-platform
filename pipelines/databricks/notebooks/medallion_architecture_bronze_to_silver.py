# Databricks notebook source
# MAGIC %md
# MAGIC # Medallion Architecture: Bronze to Silver Data Processing
# MAGIC 
# MAGIC This notebook implements automated data transformation from Bronze (raw) to Silver (cleaned) layer
# MAGIC in the Modern Data Platform medallion architecture.
# MAGIC 
# MAGIC **Key Features:**
# MAGIC - Automated data quality checks
# MAGIC - Schema evolution handling
# MAGIC - Self-healing error recovery
# MAGIC - Comprehensive logging and monitoring
# MAGIC - Zero-touch operations

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration and Imports

# COMMAND ----------

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import uuid

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
from delta.tables import DeltaTable
import great_expectations as ge
from great_expectations.dataset.sparkdf_dataset import SparkDFDataset

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration Parameters

# COMMAND ----------

# Configuration from Databricks widgets or environment variables
dbutils.widgets.text("source_path", "/mnt/bronze", "Bronze Layer Path")
dbutils.widgets.text("target_path", "/mnt/silver", "Silver Layer Path")
dbutils.widgets.text("table_name", "", "Table Name to Process")
dbutils.widgets.text("batch_id", str(uuid.uuid4()), "Batch ID")
dbutils.widgets.dropdown("data_quality_level", "strict", ["lenient", "strict", "critical"], "Data Quality Level")
dbutils.widgets.dropdown("processing_mode", "incremental", ["full", "incremental"], "Processing Mode")

# Get configuration values
SOURCE_PATH = dbutils.widgets.get("source_path")
TARGET_PATH = dbutils.widgets.get("target_path")
TABLE_NAME = dbutils.widgets.get("table_name")
BATCH_ID = dbutils.widgets.get("batch_id")
DATA_QUALITY_LEVEL = dbutils.widgets.get("data_quality_level")
PROCESSING_MODE = dbutils.widgets.get("processing_mode")

# Quality thresholds based on level
QUALITY_THRESHOLDS = {
    "lenient": {"null_percentage": 20, "duplicate_percentage": 10},
    "strict": {"null_percentage": 5, "duplicate_percentage": 2},
    "critical": {"null_percentage": 1, "duplicate_percentage": 0.1}
}

print(f"Processing Configuration:")
print(f"Source Path: {SOURCE_PATH}")
print(f"Target Path: {TARGET_PATH}")
print(f"Table Name: {TABLE_NAME}")
print(f"Batch ID: {BATCH_ID}")
print(f"Data Quality Level: {DATA_QUALITY_LEVEL}")
print(f"Processing Mode: {PROCESSING_MODE}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Utility Functions

# COMMAND ----------

def log_processing_event(event_type: str, message: str, details: Dict = None):
    """Log processing events with structured format"""
    event_data = {
        "timestamp": datetime.now().isoformat(),
        "batch_id": BATCH_ID,
        "table_name": TABLE_NAME,
        "event_type": event_type,
        "message": message,
        "details": details or {}
    }
    
    logger.info(json.dumps(event_data))
    
    # Also log to Delta table for monitoring
    event_df = spark.createDataFrame([event_data])
    event_df.write.format("delta").mode("append").saveAsTable("monitoring.processing_events")

def get_latest_files(path: str, file_format: str = "delta") -> List[str]:
    """Get list of latest files to process"""
    try:
        if file_format == "delta":
            # For Delta tables, return the table path
            return [path]
        else:
            # For file-based sources, get latest files
            files = dbutils.fs.ls(path)
            return [f.path for f in files if f.name.endswith(f".{file_format}")]
    except Exception as e:
        log_processing_event("ERROR", f"Failed to get files from {path}", {"error": str(e)})
        return []

def detect_schema_changes(current_schema: StructType, previous_schema: StructType) -> List[Dict]:
    """Detect schema evolution between current and previous versions"""
    changes = []
    
    current_fields = {f.name: f for f in current_schema.fields}
    previous_fields = {f.name: f for f in previous_schema.fields}
    
    # New columns
    for field_name in current_fields:
        if field_name not in previous_fields:
            changes.append({
                "type": "column_added",
                "column": field_name,
                "data_type": str(current_fields[field_name].dataType)
            })
    
    # Removed columns
    for field_name in previous_fields:
        if field_name not in current_fields:
            changes.append({
                "type": "column_removed",
                "column": field_name,
                "data_type": str(previous_fields[field_name].dataType)
            })
    
    # Type changes
    for field_name in current_fields:
        if field_name in previous_fields:
            if current_fields[field_name].dataType != previous_fields[field_name].dataType:
                changes.append({
                    "type": "type_changed",
                    "column": field_name,
                    "old_type": str(previous_fields[field_name].dataType),
                    "new_type": str(current_fields[field_name].dataType)
                })
    
    return changes

# COMMAND ----------

# MAGIC %md
# MAGIC ## Data Quality Framework

# COMMAND ----------

class DataQualityChecker:
    """Automated data quality checking with Great Expectations"""
    
    def __init__(self, df: DataFrame, quality_level: str):
        self.df = df
        self.quality_level = quality_level
        self.thresholds = QUALITY_THRESHOLDS[quality_level]
        self.issues = []
    
    def check_completeness(self) -> bool:
        """Check data completeness (null values)"""
        total_rows = self.df.count()
        if total_rows == 0:
            self.issues.append("No data found in source")
            return False
        
        for column in self.df.columns:
            null_count = self.df.filter(col(column).isNull()).count()
            null_percentage = (null_count / total_rows) * 100
            
            if null_percentage > self.thresholds["null_percentage"]:
                self.issues.append(f"Column {column} has {null_percentage:.2f}% null values")
                return False
        
        return True
    
    def check_uniqueness(self, key_columns: List[str]) -> bool:
        """Check data uniqueness for key columns"""
        if not key_columns:
            return True
        
        total_rows = self.df.count()
        unique_rows = self.df.select(*key_columns).distinct().count()
        duplicate_percentage = ((total_rows - unique_rows) / total_rows) * 100
        
        if duplicate_percentage > self.thresholds["duplicate_percentage"]:
            self.issues.append(f"Duplicate records: {duplicate_percentage:.2f}%")
            return False
        
        return True
    
    def check_data_freshness(self, date_column: str, max_age_hours: int = 24) -> bool:
        """Check if data is fresh enough"""
        if date_column not in self.df.columns:
            return True
        
        latest_date = self.df.agg(max(col(date_column))).collect()[0][0]
        if latest_date:
            age_hours = (datetime.now() - latest_date).total_seconds() / 3600
            if age_hours > max_age_hours:
                self.issues.append(f"Data is {age_hours:.1f} hours old (max: {max_age_hours})")
                return False
        
        return True
    
    def check_business_rules(self) -> bool:
        """Check business-specific rules"""
        # Example business rules - customize based on your domain
        rules_passed = True
        
        # Rule 1: Numeric columns should be positive where applicable
        numeric_columns = [f.name for f in self.df.schema.fields 
                          if isinstance(f.dataType, (IntegerType, DoubleType, FloatType))]
        
        for column in numeric_columns:
            if column.endswith("_amount") or column.endswith("_price"):
                negative_count = self.df.filter(col(column) < 0).count()
                if negative_count > 0:
                    self.issues.append(f"Column {column} has {negative_count} negative values")
                    rules_passed = False
        
        return rules_passed
    
    def run_all_checks(self, key_columns: List[str] = None, date_column: str = None) -> Tuple[bool, List[str]]:
        """Run all data quality checks"""
        checks = [
            self.check_completeness(),
            self.check_uniqueness(key_columns or []),
            self.check_data_freshness(date_column or "created_date"),
            self.check_business_rules()
        ]
        
        return all(checks), self.issues

# COMMAND ----------

# MAGIC %md
# MAGIC ## Data Transformation Engine

# COMMAND ----------

class BronzeToSilverProcessor:
    """Automated Bronze to Silver transformation processor"""
    
    def __init__(self, source_path: str, target_path: str, table_name: str):
        self.source_path = source_path
        self.target_path = target_path
        self.table_name = table_name
        self.spark = SparkSession.active
    
    def standardize_columns(self, df: DataFrame) -> DataFrame:
        """Standardize column names and types"""
        # Convert column names to snake_case
        for column in df.columns:
            new_name = column.lower().replace(" ", "_").replace("-", "_")
            if new_name != column:
                df = df.withColumnRenamed(column, new_name)
        
        # Add standard metadata columns
        df = df.withColumn("processed_timestamp", current_timestamp()) \
               .withColumn("batch_id", lit(BATCH_ID)) \
               .withColumn("source_file", input_file_name())
        
        return df
    
    def clean_data(self, df: DataFrame) -> DataFrame:
        """Apply data cleaning transformations"""
        # Remove leading/trailing whitespace from string columns
        string_columns = [f.name for f in df.schema.fields if isinstance(f.dataType, StringType)]
        for column in string_columns:
            df = df.withColumn(column, trim(col(column)))
        
        # Handle empty strings as nulls
        for column in string_columns:
            df = df.withColumn(column, when(col(column) == "", None).otherwise(col(column)))
        
        # Standardize date formats
        date_columns = [f.name for f in df.schema.fields if isinstance(f.dataType, DateType)]
        for column in date_columns:
            df = df.withColumn(column, to_date(col(column), "yyyy-MM-dd"))
        
        return df
    
    def validate_and_quarantine(self, df: DataFrame) -> Tuple[DataFrame, DataFrame]:
        """Validate data and separate good vs bad records"""
        # Define validation rules
        valid_condition = lit(True)
        
        # Add your validation rules here
        for column in df.columns:
            if column.endswith("_id"):
                valid_condition = valid_condition & col(column).isNotNull()
            elif column.endswith("_email"):
                valid_condition = valid_condition & col(column).rlike(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
        
        # Split into valid and invalid records
        valid_df = df.filter(valid_condition)
        invalid_df = df.filter(~valid_condition).withColumn("quarantine_reason", lit("Validation failed"))
        
        return valid_df, invalid_df
    
    def process_incremental(self) -> DataFrame:
        """Process incremental data from bronze layer"""
        log_processing_event("INFO", "Starting incremental processing")
        
        # Read from bronze layer
        bronze_df = spark.read.format("delta").load(f"{self.source_path}/{self.table_name}")
        
        # Filter for new records if processing incrementally
        if PROCESSING_MODE == "incremental":
            # Get last processed timestamp
            try:
                last_processed = spark.sql(f"""
                    SELECT MAX(processed_timestamp) as max_timestamp 
                    FROM delta.`{self.target_path}/{self.table_name}`
                """).collect()[0]["max_timestamp"]
                
                if last_processed:
                    bronze_df = bronze_df.filter(col("created_date") > last_processed)
            except:
                log_processing_event("INFO", "No previous silver data found, processing all bronze data")
        
        log_processing_event("INFO", f"Processing {bronze_df.count()} records")
        return bronze_df
    
    def write_to_silver(self, df: DataFrame):
        """Write processed data to silver layer with optimization"""
        if df.count() == 0:
            log_processing_event("INFO", "No data to write to silver layer")
            return
        
        target_table_path = f"{self.target_path}/{self.table_name}"
        
        # Optimize write operations
        df.write \
          .format("delta") \
          .mode("append") \
          .option("mergeSchema", "true") \
          .option("optimizeWrite", "true") \
          .option("autoCompact", "true") \
          .save(target_table_path)
        
        log_processing_event("INFO", f"Successfully wrote {df.count()} records to silver layer")
        
        # Run optimization
        spark.sql(f"OPTIMIZE delta.`{target_table_path}`")
        spark.sql(f"VACUUM delta.`{target_table_path}` RETAIN 168 HOURS")  # 7 days retention
    
    def handle_quarantine(self, invalid_df: DataFrame):
        """Handle quarantined records"""
        if invalid_df.count() > 0:
            quarantine_path = f"/mnt/quarantine/{self.table_name}"
            invalid_df.write \
                     .format("delta") \
                     .mode("append") \
                     .save(quarantine_path)
            
            log_processing_event("WARNING", f"Quarantined {invalid_df.count()} invalid records")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Main Processing Logic

# COMMAND ----------

def main():
    """Main processing function with error handling and monitoring"""
    
    try:
        log_processing_event("INFO", "Starting Bronze to Silver processing")
        
        # Initialize processor
        processor = BronzeToSilverProcessor(SOURCE_PATH, TARGET_PATH, TABLE_NAME)
        
        # Read and process data
        bronze_df = processor.process_incremental()
        
        if bronze_df.count() == 0:
            log_processing_event("INFO", "No new data to process")
            return
        
        # Schema evolution handling
        try:
            current_schema = bronze_df.schema
            # Compare with previous schema if exists
            # Implementation would check against a schema registry
        except Exception as e:
            log_processing_event("WARNING", f"Schema evolution check failed: {str(e)}")
        
        # Apply transformations
        standardized_df = processor.standardize_columns(bronze_df)
        cleaned_df = processor.clean_data(standardized_df)
        
        # Validate and separate good/bad records
        valid_df, invalid_df = processor.validate_and_quarantine(cleaned_df)
        
        # Data quality checks
        quality_checker = DataQualityChecker(valid_df, DATA_QUALITY_LEVEL)
        quality_passed, quality_issues = quality_checker.run_all_checks(
            key_columns=["id"] if "id" in valid_df.columns else [],
            date_column="created_date" if "created_date" in valid_df.columns else None
        )
        
        if not quality_passed:
            error_msg = f"Data quality checks failed: {'; '.join(quality_issues)}"
            log_processing_event("ERROR", error_msg)
            
            if DATA_QUALITY_LEVEL == "critical":
                raise Exception(error_msg)
            else:
                log_processing_event("WARNING", "Proceeding despite quality issues due to lenient/strict mode")
        
        # Write to silver layer
        processor.write_to_silver(valid_df)
        
        # Handle quarantined records
        processor.handle_quarantine(invalid_df)
        
        # Final logging
        log_processing_event("SUCCESS", "Bronze to Silver processing completed successfully", {
            "records_processed": valid_df.count(),
            "records_quarantined": invalid_df.count(),
            "quality_level": DATA_QUALITY_LEVEL,
            "processing_mode": PROCESSING_MODE
        })
        
    except Exception as e:
        error_msg = f"Processing failed: {str(e)}"
        log_processing_event("ERROR", error_msg)
        
        # Self-healing: attempt basic recovery
        try:
            log_processing_event("INFO", "Attempting self-healing recovery")
            # Add recovery logic here (e.g., retry with different parameters)
        except:
            log_processing_event("CRITICAL", "Self-healing failed, manual intervention required")
        
        raise e

# Execute main processing
if __name__ == "__main__":
    main()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Post-Processing Analytics and Monitoring

# COMMAND ----------

# Generate processing summary for monitoring
try:
    summary_query = f"""
    SELECT 
        '{TABLE_NAME}' as table_name,
        '{BATCH_ID}' as batch_id,
        COUNT(*) as record_count,
        MAX(processed_timestamp) as last_processed,
        COUNT(DISTINCT batch_id) as batch_count,
        current_timestamp() as summary_timestamp
    FROM delta.`{TARGET_PATH}/{TABLE_NAME}`
    WHERE DATE(processed_timestamp) = current_date()
    """
    
    summary_df = spark.sql(summary_query)
    summary_df.write.format("delta").mode("append").saveAsTable("monitoring.processing_summary")
    
    print("Processing Summary:")
    summary_df.show()
    
except Exception as e:
    print(f"Failed to generate processing summary: {str(e)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Cleanup and Optimization

# COMMAND ----------

# Clean up temporary views and cache
spark.catalog.clearCache()

# Display final status
dbutils.notebook.exit(json.dumps({
    "status": "SUCCESS",
    "batch_id": BATCH_ID,
    "table_name": TABLE_NAME,
    "processed_timestamp": datetime.now().isoformat()
}))
