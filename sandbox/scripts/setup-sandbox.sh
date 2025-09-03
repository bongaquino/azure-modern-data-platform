#!/bin/bash

# Azure Modern Data Platform - Sandbox Setup Script
# Initializes local development environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         Azure Modern Data Platform - Local Sandbox            ║${NC}"
echo -e "${BLUE}║                    Setup & Initialization                      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to print section headers
print_section() {
    echo -e "\n${BLUE}▓▓▓ $1 ▓▓▓${NC}"
}

# Function to print success messages
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Function to print warnings
print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Function to print errors
print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker Desktop and try again."
        exit 1
    fi
    print_success "Docker is running"
}

# Create required directories
create_directories() {
    print_section "Creating Directory Structure"
    
    # Data directories
    mkdir -p data/{bronze,silver,gold,raw,processed,quarantine}
    mkdir -p pipelines/airflow/dags
    mkdir -p config/{grafana,prometheus}
    mkdir -p notebooks/examples
    
    print_success "Directory structure created"
}

# Install Python dependencies
install_dependencies() {
    print_section "Installing Python Dependencies"
    
    # Create requirements file for sandbox
    cat > requirements.txt << EOF
pyspark==3.5.0
delta-spark==2.4.0
great-expectations==0.17.23
pandas==2.0.3
numpy==1.24.3
jupyter==1.0.0
matplotlib==3.7.2
seaborn==0.12.2
plotly==5.15.0
psycopg2-binary==2.9.7
pymongo==4.5.0
boto3==1.28.25
minio==7.1.16
redis==4.6.0
sqlalchemy==2.0.19
apache-airflow==2.7.0
streamlit==1.25.0
fastapi==0.101.1
uvicorn==0.23.2
EOF

    if command -v pip3 &> /dev/null; then
        pip3 install -r requirements.txt
        print_success "Python dependencies installed"
    else
        print_warning "pip3 not found. Please install dependencies manually:"
        echo "pip3 install -r requirements.txt"
    fi
}

# Create configuration files
create_configs() {
    print_section "Creating Configuration Files"
    
    # Prometheus configuration
    cat > config/prometheus.yml << EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  # - "first_rules.yml"
  # - "second_rules.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
  
  - job_name: 'spark-master'
    static_configs:
      - targets: ['spark-master:8080']
  
  - job_name: 'minio'
    static_configs:
      - targets: ['minio:9000']
EOF

    # Grafana datasources
    mkdir -p config/grafana/datasources
    cat > config/grafana/datasources/prometheus.yml << EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
EOF

    # Database initialization script
    cat > scripts/init-db.sql << EOF
-- Sample database schema for demonstration
CREATE SCHEMA IF NOT EXISTS sales;
CREATE SCHEMA IF NOT EXISTS customers;
CREATE SCHEMA IF NOT EXISTS products;

-- Sample sales data
CREATE TABLE sales.transactions (
    transaction_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50),
    product_id VARCHAR(50),
    sale_amount DECIMAL(10,2),
    sale_date DATE,
    sale_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    store_location VARCHAR(100),
    payment_method VARCHAR(50)
);

-- Sample customer data
CREATE TABLE customers.profiles (
    customer_id VARCHAR(50) PRIMARY KEY,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(200),
    phone VARCHAR(20),
    registration_date DATE,
    customer_segment VARCHAR(50),
    total_lifetime_value DECIMAL(12,2)
);

-- Sample product data
CREATE TABLE products.catalog (
    product_id VARCHAR(50) PRIMARY KEY,
    product_name VARCHAR(200),
    category VARCHAR(100),
    subcategory VARCHAR(100),
    price DECIMAL(10,2),
    cost DECIMAL(10,2),
    supplier VARCHAR(100),
    launch_date DATE
);

-- Insert sample data
INSERT INTO sales.transactions VALUES
('TXN001', 'CUST001', 'PROD001', 299.99, '2024-01-15', '2024-01-15 10:30:00', 'New York', 'Credit Card'),
('TXN002', 'CUST002', 'PROD002', 149.99, '2024-01-15', '2024-01-15 11:45:00', 'California', 'Debit Card'),
('TXN003', 'CUST001', 'PROD003', 599.99, '2024-01-16', '2024-01-16 09:15:00', 'New York', 'Credit Card'),
('TXN004', 'CUST003', 'PROD001', 299.99, '2024-01-16', '2024-01-16 14:20:00', 'Texas', 'Cash'),
('TXN005', 'CUST002', 'PROD004', 89.99, '2024-01-17', '2024-01-17 16:00:00', 'California', 'Credit Card');

INSERT INTO customers.profiles VALUES
('CUST001', 'John', 'Doe', 'john.doe@email.com', '555-0101', '2023-06-15', 'Premium', 1299.97),
('CUST002', 'Jane', 'Smith', 'jane.smith@email.com', '555-0102', '2023-08-22', 'Standard', 239.98),
('CUST003', 'Bob', 'Johnson', 'bob.johnson@email.com', '555-0103', '2023-12-01', 'New', 299.99);

INSERT INTO products.catalog VALUES
('PROD001', 'Wireless Headphones', 'Electronics', 'Audio', 299.99, 150.00, 'AudioTech Inc', '2023-01-01'),
('PROD002', 'Bluetooth Speaker', 'Electronics', 'Audio', 149.99, 75.00, 'SoundCorp', '2023-02-15'),
('PROD003', 'Smartphone Case', 'Accessories', 'Phone', 599.99, 300.00, 'CaseMaker Ltd', '2023-03-01'),
('PROD004', 'USB Cable', 'Accessories', 'Cables', 89.99, 45.00, 'CableCo', '2023-04-10');
EOF

    print_success "Configuration files created"
}

# Create sample notebooks
create_sample_notebooks() {
    print_section "Creating Sample Jupyter Notebooks"
    
    # Medallion Architecture Demo Notebook
    cat > notebooks/medallion_architecture_demo.ipynb << 'EOF'
{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Medallion Architecture Demo\n",
    "## Bronze → Silver → Gold Data Pipeline\n",
    "\n",
    "This notebook demonstrates the medallion architecture pattern using local Spark and Delta Lake."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Initialize Spark Session with Delta Lake\n",
    "from pyspark.sql import SparkSession\n",
    "from pyspark.sql.functions import *\n",
    "from delta import configure_spark_with_delta_pip\n",
    "\n",
    "builder = SparkSession.builder.appName(\"MedallionDemo\") \\\n",
    "    .config(\"spark.sql.extensions\", \"io.delta.sql.DeltaSparkSessionExtension\") \\\n",
    "    .config(\"spark.sql.catalog.spark_catalog\", \"org.apache.spark.sql.delta.catalog.DeltaCatalog\") \\\n",
    "    .config(\"spark.master\", \"spark://spark-master:7077\")\n",
    "\n",
    "spark = configure_spark_with_delta_pip(builder).getOrCreate()\n",
    "print(\"✅ Spark Session initialized with Delta Lake support\")"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Bronze Layer: Load raw data\n",
    "print(\"🥉 Bronze Layer: Loading raw data...\")\n",
    "\n",
    "# Simulate loading from PostgreSQL\n",
    "bronze_sales = spark.read \\\n",
    "    .format(\"jdbc\") \\\n",
    "    .option(\"url\", \"jdbc:postgresql://postgres:5432/sandbox_db\") \\\n",
    "    .option(\"dbtable\", \"sales.transactions\") \\\n",
    "    .option(\"user\", \"sandbox_user\") \\\n",
    "    .option(\"password\", \"sandbox_pass\") \\\n",
    "    .load()\n",
    "\n",
    "# Add metadata columns\n",
    "bronze_sales = bronze_sales \\\n",
    "    .withColumn(\"ingestion_timestamp\", current_timestamp()) \\\n",
    "    .withColumn(\"source_system\", lit(\"postgres_sales\"))\n",
    "\n",
    "# Write to Bronze Delta table\n",
    "bronze_sales.write \\\n",
    "    .format(\"delta\") \\\n",
    "    .mode(\"overwrite\") \\\n",
    "    .save(\"/opt/bitnami/spark/data/bronze/sales\")\n",
    "\n",
    "print(f\"✅ Bronze layer created with {bronze_sales.count()} records\")\n",
    "bronze_sales.show(5)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Silver Layer: Clean and validate data\n",
    "print(\"🥈 Silver Layer: Cleaning and validating data...\")\n",
    "\n",
    "# Read from Bronze\n",
    "bronze_df = spark.read.format(\"delta\").load(\"/opt/bitnami/spark/data/bronze/sales\")\n",
    "\n",
    "# Data cleaning and validation\n",
    "silver_sales = bronze_df \\\n",
    "    .filter(col(\"sale_amount\") > 0) \\\n",
    "    .filter(col(\"customer_id\").isNotNull()) \\\n",
    "    .withColumn(\"sale_amount\", col(\"sale_amount\").cast(\"decimal(10,2)\")) \\\n",
    "    .withColumn(\"processed_timestamp\", current_timestamp()) \\\n",
    "    .withColumn(\"data_quality_score\", lit(100.0))\n",
    "\n",
    "# Write to Silver Delta table\n",
    "silver_sales.write \\\n",
    "    .format(\"delta\") \\\n",
    "    .mode(\"overwrite\") \\\n",
    "    .save(\"/opt/bitnami/spark/data/silver/sales\")\n",
    "\n",
    "print(f\"✅ Silver layer created with {silver_sales.count()} records\")\n",
    "silver_sales.show(5)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Gold Layer: Business aggregations\n",
    "print(\"🥇 Gold Layer: Creating business aggregations...\")\n",
    "\n",
    "# Read from Silver\n",
    "silver_df = spark.read.format(\"delta\").load(\"/opt/bitnami/spark/data/silver/sales\")\n",
    "\n",
    "# Business aggregations\n",
    "gold_daily_sales = silver_df \\\n",
    "    .groupBy(\"sale_date\", \"store_location\") \\\n",
    "    .agg(\n",
    "        count(\"transaction_id\").alias(\"transaction_count\"),\n",
    "        sum(\"sale_amount\").alias(\"total_sales\"),\n",
    "        avg(\"sale_amount\").alias(\"avg_transaction_value\"),\n",
    "        countDistinct(\"customer_id\").alias(\"unique_customers\")\n",
    "    ) \\\n",
    "    .withColumn(\"processed_timestamp\", current_timestamp())\n",
    "\n",
    "# Write to Gold Delta table\n",
    "gold_daily_sales.write \\\n",
    "    .format(\"delta\") \\\n",
    "    .mode(\"overwrite\") \\\n",
    "    .save(\"/opt/bitnami/spark/data/gold/daily_sales\")\n",
    "\n",
    "print(f\"✅ Gold layer created with {gold_daily_sales.count()} records\")\n",
    "gold_daily_sales.show()"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Demonstrate Delta Lake features\n",
    "print(\"🔍 Delta Lake Features Demo...\")\n",
    "\n",
    "# Show table history\n",
    "spark.sql(\"DESCRIBE HISTORY delta.`/opt/bitnami/spark/data/silver/sales`\").show()\n",
    "\n",
    "# Show table details\n",
    "spark.sql(\"DESCRIBE DETAIL delta.`/opt/bitnami/spark/data/silver/sales`\").show()\n",
    "\n",
    "print(\"✅ Medallion Architecture Demo Complete!\")"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.11.0"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}
EOF

    print_success "Sample notebooks created"
}

# Main setup function
main() {
    print_section "Starting Sandbox Setup"
    
    check_docker
    create_directories
    install_dependencies
    create_configs
    create_sample_notebooks
    
    print_section "Setup Complete"
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                    SETUP SUCCESSFUL                           ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "🚀 Next Steps:"
    echo "   1. Start the sandbox: docker-compose up -d"
    echo "   2. Wait for all services to start (about 2-3 minutes)"
    echo "   3. Access Jupyter Lab: http://localhost:8888 (token: sandbox)"
    echo "   4. Run the medallion architecture demo notebook"
    echo ""
    echo "📊 Service URLs:"
    echo "   • Jupyter Lab: http://localhost:8888"
    echo "   • Spark Master UI: http://localhost:8080"
    echo "   • MinIO Console: http://localhost:9001"
    echo "   • Airflow: http://localhost:8081"
    echo "   • Grafana: http://localhost:3000"
    echo "   • Prometheus: http://localhost:9090"
    echo ""
    echo "🔐 Default Credentials:"
    echo "   • MinIO: admin/password123"
    echo "   • Grafana: admin/admin"
    echo "   • Jupyter: token 'sandbox'"
}

# Run the main function
main
