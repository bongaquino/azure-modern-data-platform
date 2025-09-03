#!/bin/bash

# Azure Modern Data Platform - Sandbox Quick Start
# One-command setup and demo for local development

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       Azure Modern Data Platform - Local Sandbox              ║${NC}"
echo -e "${BLUE}║              Quick Start & Demo                                ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if we're in the sandbox directory
if [[ ! -f "docker-compose.yml" ]]; then
    echo "Navigating to sandbox directory..."
    cd sandbox
fi

echo -e "${BLUE}🔧 Setting up local development environment...${NC}"

# Run setup script
echo "Running initial setup..."
chmod +x scripts/setup-sandbox.sh
./scripts/setup-sandbox.sh

echo -e "\n${BLUE}🐳 Starting Docker services...${NC}"
echo "This may take a few minutes on first run..."

# Start Docker services
docker-compose up -d

echo -e "\n${YELLOW}⏳ Waiting for services to start...${NC}"
sleep 30

echo -e "\n${BLUE}📊 Running Medallion Architecture Demo...${NC}"

# Install Python dependencies locally
pip3 install pyspark==3.5.0 pandas numpy great-expectations 2>/dev/null || echo "Dependencies already installed"

# Run the demo
python3 pipelines/medallion_demo.py

echo -e "\n${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    SANDBOX READY!                             ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "🎯 Access Points:"
echo "   • Jupyter Lab: http://localhost:8888 (token: sandbox)"
echo "   • Spark Master UI: http://localhost:8080"
echo "   • MinIO Console: http://localhost:9001 (admin/password123)"
echo "   • Grafana: http://localhost:3000 (admin/admin)"
echo ""
echo "📁 Generated Data:"
echo "   • Bronze Layer: data/bronze/sales"
echo "   • Silver Layer: data/silver/sales"
echo "   • Gold Layer: data/gold/"
echo ""
echo "🎮 Try These Next:"
echo "   1. Open Jupyter notebook: medallion_architecture_demo.ipynb"
echo "   2. Explore data in different layers"
echo "   3. Experiment with Spark SQL queries"
echo "   4. Set up custom monitoring dashboards"
echo ""
echo "🛑 To stop sandbox:"
echo "   docker-compose down"
