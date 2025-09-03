# Local Development Sandbox
## Azure Modern Data Platform - Local Testing Environment

This sandbox provides a complete local development environment that simulates the Azure Modern Data Platform using Docker containers and local tools. Perfect for development, testing, and demonstration without Azure costs.

## 🎯 Sandbox Overview

### What This Provides:
- **Local Spark Environment**: Databricks-like experience with PySpark
- **Delta Lake Storage**: Local Delta tables for medallion architecture
- **Minio Storage**: S3-compatible storage simulating Azure Data Lake
- **PostgreSQL**: Metadata store and sample data source
- **Jupyter Notebooks**: Interactive development environment
- **Monitoring Stack**: Prometheus + Grafana for observability
- **Airflow**: Workflow orchestration simulating Azure Data Factory

### Architecture Simulation:
```
Local Machine
├── 🐳 Docker Containers
│   ├── Spark Master + Workers (Databricks simulation)
│   ├── Minio (Azure Data Lake simulation)
│   ├── PostgreSQL (Sample data source)
│   ├── Jupyter Lab (Development environment)
│   ├── Airflow (Azure Data Factory simulation)
│   └── Prometheus + Grafana (Monitoring)
├── 📁 Local Storage
│   ├── Bronze Layer (Raw data)
│   ├── Silver Layer (Cleaned data)
│   └── Gold Layer (Analytics-ready data)
└── 🔧 Development Tools
    ├── Python + PySpark
    ├── Delta Lake
    └── Great Expectations
```

## 🚀 Quick Start

### Prerequisites:
- Docker Desktop
- Python 3.9+
- Git

### Setup Commands:
```bash
# Navigate to sandbox
cd sandbox

# Start all services
docker-compose up -d

# Initialize the environment
./scripts/setup-sandbox.sh

# Run sample data pipeline
python pipelines/medallion_demo.py
```

## 📊 Access Points:
- **Jupyter Lab**: http://localhost:8888 (token: `sandbox`)
- **Spark UI**: http://localhost:4040
- **Minio Console**: http://localhost:9001 (admin/password)
- **Airflow**: http://localhost:8080 (admin/admin)
- **Grafana**: http://localhost:3000 (admin/admin)

## 🎮 Demo Scenarios:
1. **End-to-End Pipeline**: Bronze → Silver → Gold data flow
2. **Data Quality Checks**: Automated validation and remediation
3. **Schema Evolution**: Handle changing data structures
4. **Performance Monitoring**: Resource usage and query metrics
5. **Error Handling**: Simulate and recover from failures
