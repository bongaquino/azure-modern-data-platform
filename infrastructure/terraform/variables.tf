# Variables for Azure Modern Data Platform
# Comprehensive variable definitions for automated infrastructure

# Core Configuration
variable "project_name" {
  description = "Name of the project - used for resource naming"
  type        = string
  default     = "mdp"
  
  validation {
    condition     = length(var.project_name) >= 2 && length(var.project_name) <= 10
    error_message = "Project name must be between 2 and 10 characters."
  }
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "location" {
  description = "Azure region for resource deployment"
  type        = string
  default     = "East US 2"
}

variable "owner" {
  description = "Owner of the resources"
  type        = string
  default     = "Cloud Engineering Team"
}

variable "cost_center" {
  description = "Cost center for billing"
  type        = string
  default     = "Data Platform"
}

variable "common_tags" {
  description = "Common tags to be applied to all resources"
  type        = map(string)
  default = {
    Purpose      = "Modern Data Platform"
    Automation   = "Terraform"
    DataClass    = "Confidential"
    Compliance   = "GDPR,HIPAA,SOC2"
  }
}

# Networking Configuration
variable "vnet_address_space" {
  description = "Address space for the virtual network"
  type        = list(string)
  default     = ["10.0.0.0/16"]
}

variable "subnet_config" {
  description = "Subnet configuration for the virtual network"
  type = map(object({
    address_prefixes = list(string)
    service_endpoints = list(string)
    delegation = optional(object({
      name = string
      service_delegation = object({
        name    = string
        actions = list(string)
      })
    }))
  }))
  default = {
    databricks_private = {
      address_prefixes  = ["10.0.1.0/24"]
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
      address_prefixes  = ["10.0.2.0/24"]
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
      address_prefixes  = ["10.0.3.0/24"]
      service_endpoints = ["Microsoft.Storage", "Microsoft.KeyVault"]
    }
    data_gateway = {
      address_prefixes  = ["10.0.4.0/24"]
      service_endpoints = ["Microsoft.Storage"]
    }
  }
}

variable "enable_ddos_protection" {
  description = "Enable DDoS protection standard"
  type        = bool
  default     = false
}

variable "dns_servers" {
  description = "Custom DNS servers for the virtual network"
  type        = list(string)
  default     = []
}

# Security Configuration
variable "key_vault_sku" {
  description = "SKU for Key Vault"
  type        = string
  default     = "standard"
  
  validation {
    condition     = contains(["standard", "premium"], var.key_vault_sku)
    error_message = "Key Vault SKU must be either 'standard' or 'premium'."
  }
}

variable "purge_protection_enabled" {
  description = "Enable purge protection for Key Vault"
  type        = bool
  default     = true
}

variable "soft_delete_retention_days" {
  description = "Number of days to retain soft-deleted items"
  type        = number
  default     = 90
  
  validation {
    condition     = var.soft_delete_retention_days >= 7 && var.soft_delete_retention_days <= 90
    error_message = "Soft delete retention days must be between 7 and 90."
  }
}

variable "admin_object_ids" {
  description = "Object IDs of administrators for Key Vault access"
  type        = list(string)
  default     = []
}

# Data Lake Configuration
variable "storage_account_tier" {
  description = "Performance tier for storage account"
  type        = string
  default     = "Standard"
  
  validation {
    condition     = contains(["Standard", "Premium"], var.storage_account_tier)
    error_message = "Storage account tier must be either 'Standard' or 'Premium'."
  }
}

variable "storage_replication_type" {
  description = "Replication type for storage account"
  type        = string
  default     = "ZRS"
  
  validation {
    condition     = contains(["LRS", "GRS", "RAGRS", "ZRS", "GZRS", "RAGZRS"], var.storage_replication_type)
    error_message = "Invalid storage replication type."
  }
}

variable "enable_versioning" {
  description = "Enable blob versioning for data lake"
  type        = bool
  default     = true
}

variable "data_lake_containers" {
  description = "Data lake containers configuration"
  type = map(object({
    access_type = string
    metadata    = map(string)
  }))
  default = {
    bronze = {
      access_type = "private"
      metadata = {
        layer       = "bronze"
        description = "Raw data ingestion layer"
        retention   = "7-years"
      }
    }
    silver = {
      access_type = "private"
      metadata = {
        layer       = "silver"
        description = "Cleaned and validated data layer"
        retention   = "7-years"
      }
    }
    gold = {
      access_type = "private"
      metadata = {
        layer       = "gold"
        description = "Business-ready analytics layer"
        retention   = "7-years"
      }
    }
    archive = {
      access_type = "private"
      metadata = {
        layer       = "archive"
        description = "Long-term data archival"
        retention   = "permanent"
      }
    }
    quarantine = {
      access_type = "private"
      metadata = {
        layer       = "quarantine"
        description = "Data quality failure isolation"
        retention   = "30-days"
      }
    }
  }
}

# Databricks Configuration
variable "databricks_sku" {
  description = "SKU for Databricks workspace"
  type        = string
  default     = "premium"
  
  validation {
    condition     = contains(["standard", "premium", "trial"], var.databricks_sku)
    error_message = "Databricks SKU must be one of: standard, premium, trial."
  }
}

# Data Factory Configuration
variable "adf_github_config" {
  description = "GitHub configuration for Azure Data Factory"
  type = object({
    account_name    = string
    branch_name     = string
    git_url         = string
    repository_name = string
    root_folder     = string
  })
  default = null
}

variable "enable_self_hosted_ir" {
  description = "Enable self-hosted integration runtime"
  type        = bool
  default     = false
}

# Purview Configuration
variable "purview_sku" {
  description = "SKU for Microsoft Purview"
  type        = string
  default     = "Standard"
  
  validation {
    condition     = contains(["Standard"], var.purview_sku)
    error_message = "Purview SKU must be 'Standard'."
  }
}

# Monitoring Configuration
variable "log_retention_days" {
  description = "Log retention period in days"
  type        = number
  default     = 90
  
  validation {
    condition     = var.log_retention_days >= 30 && var.log_retention_days <= 730
    error_message = "Log retention days must be between 30 and 730."
  }
}

variable "notification_email" {
  description = "Email address for monitoring notifications"
  type        = string
  default     = ""
}

variable "enable_automated_remediation" {
  description = "Enable automated remediation for common issues"
  type        = bool
  default     = true
}

# Automation Configuration
variable "automation_functions" {
  description = "Configuration for automation functions"
  type = map(object({
    runtime_version = string
    app_settings   = map(string)
    schedule       = string
  }))
  default = {
    data_quality_monitor = {
      runtime_version = "~4"
      app_settings = {
        "FUNCTIONS_WORKER_RUNTIME" = "python"
        "PYTHON_VERSION"          = "3.9"
      }
      schedule = "0 0 * * *"  # Daily at midnight
    }
    cost_optimizer = {
      runtime_version = "~4"
      app_settings = {
        "FUNCTIONS_WORKER_RUNTIME" = "python"
        "PYTHON_VERSION"          = "3.9"
      }
      schedule = "0 6 * * 1"  # Weekly on Monday at 6 AM
    }
    pipeline_monitor = {
      runtime_version = "~4"
      app_settings = {
        "FUNCTIONS_WORKER_RUNTIME" = "python"
        "PYTHON_VERSION"          = "3.9"
      }
      schedule = "*/15 * * * *"  # Every 15 minutes
    }
  }
}

variable "logic_app_workflows" {
  description = "Configuration for Logic App workflows"
  type = map(object({
    definition = string
    parameters = map(string)
  }))
  default = {}
}

variable "event_grid_topics" {
  description = "Configuration for Event Grid topics"
  type = map(object({
    input_schema = string
    tags        = map(string)
  }))
  default = {
    data_pipeline_events = {
      input_schema = "EventGridSchema"
      tags = {
        purpose = "Data pipeline event handling"
      }
    }
    data_quality_events = {
      input_schema = "EventGridSchema"
      tags = {
        purpose = "Data quality monitoring"
      }
    }
  }
}
