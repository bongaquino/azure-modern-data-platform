# Production Environment Configuration
# Azure Modern Data Platform - Production Settings

# Core Configuration
project_name = "mdp"
environment  = "prod"
location     = "East US 2"
owner        = "Data Platform Operations"
cost_center  = "Data Platform"

# Common Tags
common_tags = {
  Purpose       = "Modern Data Platform Production"
  Environment   = "Production"
  Team         = "Data Platform Operations"
  CostCenter   = "Data Platform"
  Compliance   = "GDPR,HIPAA,SOC2,ISO27001"
  DataClass    = "Confidential"
  BackupPolicy = "Critical"
  AutoShutdown = "Disabled"
  SLA          = "99.9%"
  MonitoringLevel = "Enhanced"
}

# Networking Configuration (Production-grade addressing)
vnet_address_space = ["10.0.0.0/16"]

# Enable DDoS protection for production
enable_ddos_protection = true

subnet_config = {
  databricks_private = {
    address_prefixes  = ["10.0.1.0/24"]
    service_endpoints = ["Microsoft.Storage", "Microsoft.KeyVault", "Microsoft.Sql", "Microsoft.EventHub"]
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
    address_prefixes  = ["10.0.2.0/24"]
    service_endpoints = ["Microsoft.Storage", "Microsoft.KeyVault", "Microsoft.Sql", "Microsoft.EventHub"]
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
    address_prefixes  = ["10.0.3.0/24"]
    service_endpoints = ["Microsoft.Storage", "Microsoft.KeyVault", "Microsoft.Sql"]
  }
  data_gateway = {
    address_prefixes  = ["10.0.4.0/24"]
    service_endpoints = ["Microsoft.Storage", "Microsoft.Sql"]
  }
  application_gateway = {
    address_prefixes  = ["10.0.5.0/24"]
    service_endpoints = []
  }
  bastion = {
    address_prefixes  = ["10.0.6.0/24"]
    service_endpoints = []
  }
}

# Security Configuration (Production-hardened)
key_vault_sku = "premium"
purge_protection_enabled = true
soft_delete_retention_days = 90

# Data Lake Configuration (Production resilience)
storage_account_tier = "Standard"
storage_replication_type = "GZRS"  # Geo-zone-redundant for maximum availability
enable_versioning = true

data_lake_containers = {
  bronze = {
    access_type = "private"
    metadata = {
      layer       = "bronze"
      description = "Production raw data ingestion layer"
      retention   = "7-years"
      compliance  = "GDPR,HIPAA"
    }
  }
  silver = {
    access_type = "private"
    metadata = {
      layer       = "silver"
      description = "Production cleaned and validated data"
      retention   = "7-years"
      compliance  = "GDPR,HIPAA"
    }
  }
  gold = {
    access_type = "private"
    metadata = {
      layer       = "gold"
      description = "Production business-ready analytics"
      retention   = "7-years"
      compliance  = "GDPR,HIPAA"
    }
  }
  archive = {
    access_type = "private"
    metadata = {
      layer       = "archive"
      description = "Production long-term archival"
      retention   = "permanent"
      compliance  = "GDPR,HIPAA"
      tier       = "Archive"
    }
  }
  quarantine = {
    access_type = "private"
    metadata = {
      layer       = "quarantine"
      description = "Production data quality isolation"
      retention   = "90-days"
      compliance  = "GDPR"
    }
  }
  sensitive = {
    access_type = "private"
    metadata = {
      layer       = "sensitive"
      description = "Production PII/PHI data with enhanced security"
      retention   = "7-years"
      compliance  = "GDPR,HIPAA,PCI"
      encryption  = "CustomerManaged"
    }
  }
}

# Databricks Configuration (Production grade)
databricks_sku = "premium"

# Data Factory Configuration
enable_self_hosted_ir = true

# GitHub Configuration for Data Factory
adf_github_config = {
  account_name    = "your-org"
  branch_name     = "main"
  git_url         = "https://github.com/your-org/data-platform-pipelines.git"
  repository_name = "data-platform-pipelines"
  root_folder     = "/pipelines"
}

# Monitoring Configuration (Production monitoring)
log_retention_days = 365  # 1 year retention for compliance
notification_email = "dataplatform-alerts@company.com"
enable_automated_remediation = true

# Automation Configuration (Comprehensive production automation)
automation_functions = {
  data_quality_monitor = {
    runtime_version = "~4"
    app_settings = {
      "FUNCTIONS_WORKER_RUNTIME" = "python"
      "PYTHON_VERSION"          = "3.9"
      "ENVIRONMENT"             = "production"
      "LOG_LEVEL"               = "INFO"
      "ALERT_THRESHOLD"         = "ERROR"
    }
    schedule = "0 */4 * * *"  # Every 4 hours
  }
  cost_optimizer = {
    runtime_version = "~4"
    app_settings = {
      "FUNCTIONS_WORKER_RUNTIME" = "python"
      "PYTHON_VERSION"          = "3.9"
      "ENVIRONMENT"             = "production"
      "OPTIMIZATION_ENABLED"    = "true"
    }
    schedule = "0 2 * * *"  # Daily at 2 AM
  }
  pipeline_monitor = {
    runtime_version = "~4"
    app_settings = {
      "FUNCTIONS_WORKER_RUNTIME" = "python"
      "PYTHON_VERSION"          = "3.9"
      "ENVIRONMENT"             = "production"
      "ALERT_ON_FAILURE"        = "true"
    }
    schedule = "*/5 * * * *"  # Every 5 minutes
  }
  security_scanner = {
    runtime_version = "~4"
    app_settings = {
      "FUNCTIONS_WORKER_RUNTIME" = "python"
      "PYTHON_VERSION"          = "3.9"
      "ENVIRONMENT"             = "production"
      "SCAN_SENSITIVITY"        = "HIGH"
    }
    schedule = "0 1 * * *"  # Daily at 1 AM
  }
  backup_validator = {
    runtime_version = "~4"
    app_settings = {
      "FUNCTIONS_WORKER_RUNTIME" = "python"
      "PYTHON_VERSION"          = "3.9"
      "ENVIRONMENT"             = "production"
    }
    schedule = "0 6 * * *"  # Daily at 6 AM
  }
}

logic_app_workflows = {
  incident_response = {
    definition = "incident-response-workflow.json"
    parameters = {
      "alertThreshold" = "CRITICAL"
      "escalationEmail" = "oncall@company.com"
    }
  }
  data_lineage_tracker = {
    definition = "data-lineage-workflow.json"
    parameters = {
      "trackingInterval" = "PT1H"  # Every hour
    }
  }
}

event_grid_topics = {
  data_pipeline_events = {
    input_schema = "EventGridSchema"
    tags = {
      purpose = "Production pipeline events"
      environment = "prod"
      sla = "99.9%"
    }
  }
  data_quality_events = {
    input_schema = "EventGridSchema"
    tags = {
      purpose = "Production data quality monitoring"
      environment = "prod"
      compliance = "GDPR,HIPAA"
    }
  }
  security_events = {
    input_schema = "EventGridSchema"
    tags = {
      purpose = "Production security monitoring"
      environment = "prod"
      sensitivity = "HIGH"
    }
  }
}
