# Development Environment Configuration
# Azure Modern Data Platform - Development Settings

# Core Configuration
project_name = "mdp"
environment  = "dev"
location     = "East US 2"
owner        = "Data Engineering Team"
cost_center  = "Development"

# Common Tags
common_tags = {
  Purpose       = "Modern Data Platform Development"
  Environment   = "Development"
  Team         = "Data Engineering"
  CostCenter   = "Development"
  Compliance   = "Internal"
  DataClass    = "Internal"
  BackupPolicy = "Standard"
  AutoShutdown = "Enabled"
}

# Networking Configuration (Smaller address space for dev)
vnet_address_space = ["10.10.0.0/16"]

subnet_config = {
  databricks_private = {
    address_prefixes  = ["10.10.1.0/24"]
    service_endpoints = ["Microsoft.Storage", "Microsoft.KeyVault"]
    delegation = {
      name = "databricks-delegation"
      service_delegation = {
        name = "Microsoft.Databricks/workspaces"
        actions = [
          "Microsoft.Network/virtualNetworks/subnets/join/action",
          "Microsoft.Network/virtualNetworks/subnets/prepareNetworkPolicies/action",
          "Microsoft.Network/virtualNetworks/subnets/unprepareNetworkPolicies/action"
        ]
      }
    }
  }
  databricks_public = {
    address_prefixes  = ["10.10.2.0/24"]
    service_endpoints = ["Microsoft.Storage", "Microsoft.KeyVault"]
    delegation = {
      name = "databricks-delegation"
      service_delegation = {
        name = "Microsoft.Databricks/workspaces"
        actions = [
          "Microsoft.Network/virtualNetworks/subnets/join/action",
          "Microsoft.Network/virtualNetworks/subnets/prepareNetworkPolicies/action",
          "Microsoft.Network/virtualNetworks/subnets/unprepareNetworkPolicies/action"
        ]
      }
    }
  }
  private_endpoints = {
    address_prefixes  = ["10.10.3.0/24"]
    service_endpoints = ["Microsoft.Storage", "Microsoft.KeyVault"]
  }
  data_gateway = {
    address_prefixes  = ["10.10.4.0/24"]
    service_endpoints = ["Microsoft.Storage"]
  }
}

# Security Configuration (Relaxed for development)
key_vault_sku = "standard"
purge_protection_enabled = false
soft_delete_retention_days = 7

# Data Lake Configuration (Cost-optimized for dev)
storage_account_tier = "Standard"
storage_replication_type = "LRS"
enable_versioning = false

data_lake_containers = {
  bronze = {
    access_type = "private"
    metadata = {
      layer       = "bronze"
      description = "Development raw data ingestion"
      retention   = "30-days"
    }
  }
  silver = {
    access_type = "private"
    metadata = {
      layer       = "silver"
      description = "Development cleaned data"
      retention   = "30-days"
    }
  }
  gold = {
    access_type = "private"
    metadata = {
      layer       = "gold"
      description = "Development analytics-ready data"
      retention   = "30-days"
    }
  }
  sandbox = {
    access_type = "private"
    metadata = {
      layer       = "sandbox"
      description = "Development experimentation area"
      retention   = "7-days"
    }
  }
}

# Databricks Configuration
databricks_sku = "standard"

# Data Factory Configuration
enable_self_hosted_ir = false

# Monitoring Configuration (Reduced retention for cost)
log_retention_days = 30
notification_email = "dataeng-dev@company.com"
enable_automated_remediation = true

# Automation Configuration (Simplified for dev)
automation_functions = {
  data_quality_monitor = {
    runtime_version = "~4"
    app_settings = {
      "FUNCTIONS_WORKER_RUNTIME" = "python"
      "PYTHON_VERSION"          = "3.9"
      "ENVIRONMENT"             = "development"
    }
    schedule = "0 9 * * 1-5"  # Weekdays at 9 AM
  }
  pipeline_monitor = {
    runtime_version = "~4"
    app_settings = {
      "FUNCTIONS_WORKER_RUNTIME" = "python"
      "PYTHON_VERSION"          = "3.9"
      "ENVIRONMENT"             = "development"
    }
    schedule = "*/30 * * * *"  # Every 30 minutes
  }
}

event_grid_topics = {
  data_pipeline_events = {
    input_schema = "EventGridSchema"
    tags = {
      purpose = "Development pipeline events"
      environment = "dev"
    }
  }
}
