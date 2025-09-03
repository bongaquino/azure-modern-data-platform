# Azure Modern Data Platform - Infrastructure as Code
# Senior Cloud Engineer Demo - Automated Data Architecture

terraform {
  required_version = ">= 1.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.45"
    }
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.30"
    }
  }

  backend "azurerm" {
    # Backend configuration will be provided during terraform init
    # using partial configuration for environment-specific backends
  }
}

# Configure the Azure Provider
provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
    key_vault {
      purge_soft_delete_on_destroy    = true
      recover_soft_deleted_key_vaults = true
    }
  }
}

# Configure Azure AD Provider
provider "azuread" {}

# Local values for resource naming and configuration
locals {
  # Environment-specific naming convention
  naming_prefix = "${var.project_name}-${var.environment}"
  
  # Common tags applied to all resources
  common_tags = merge(var.common_tags, {
    Environment   = var.environment
    Project       = var.project_name
    ManagedBy     = "Terraform"
    Owner         = var.owner
    CostCenter    = var.cost_center
    CreatedDate   = timestamp()
    Architecture  = "Modern-Data-Platform"
    Automation    = "Enabled"
  })

  # Resource group names
  rg_data_platform = "${local.naming_prefix}-data-platform-rg"
  rg_networking    = "${local.naming_prefix}-networking-rg"
  rg_security      = "${local.naming_prefix}-security-rg"
  rg_monitoring    = "${local.naming_prefix}-monitoring-rg"
}

# Data sources for existing resources
data "azurerm_client_config" "current" {}

# Main Resource Groups
resource "azurerm_resource_group" "data_platform" {
  name     = local.rg_data_platform
  location = var.location
  tags     = local.common_tags
}

resource "azurerm_resource_group" "networking" {
  name     = local.rg_networking
  location = var.location
  tags     = local.common_tags
}

resource "azurerm_resource_group" "security" {
  name     = local.rg_security
  location = var.location
  tags     = local.common_tags
}

resource "azurerm_resource_group" "monitoring" {
  name     = local.rg_monitoring
  location = var.location
  tags     = local.common_tags
}

# Core Data Platform Modules
module "networking" {
  source = "./modules/networking"

  resource_group_name = azurerm_resource_group.networking.name
  location           = var.location
  naming_prefix      = local.naming_prefix
  tags               = local.common_tags
  
  # VNet Configuration
  vnet_address_space = var.vnet_address_space
  subnet_config      = var.subnet_config
  
  # Network Security
  enable_ddos_protection = var.enable_ddos_protection
  dns_servers           = var.dns_servers
}

module "security" {
  source = "./modules/security"

  resource_group_name = azurerm_resource_group.security.name
  location           = var.location
  naming_prefix      = local.naming_prefix
  tags               = local.common_tags
  
  # Key Vault Configuration
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  key_vault_sku               = var.key_vault_sku
  purge_protection_enabled    = var.purge_protection_enabled
  soft_delete_retention_days  = var.soft_delete_retention_days
  
  # Network Integration
  subnet_id = module.networking.private_endpoint_subnet_id
  
  # Access Policies
  admin_object_ids = var.admin_object_ids
}

module "data_lake" {
  source = "./modules/data-lake"

  resource_group_name = azurerm_resource_group.data_platform.name
  location           = var.location
  naming_prefix      = local.naming_prefix
  tags               = local.common_tags
  
  # Storage Configuration
  storage_account_tier         = var.storage_account_tier
  storage_replication_type     = var.storage_replication_type
  enable_hierarchical_namespace = true
  enable_versioning           = var.enable_versioning
  
  # Data Lake Structure
  containers = var.data_lake_containers
  
  # Network Integration
  subnet_id               = module.networking.private_endpoint_subnet_id
  allowed_subnet_ids      = [module.networking.databricks_private_subnet_id]
  bypass_azure_services   = true
  
  # Security
  key_vault_id = module.security.key_vault_id
}

module "databricks" {
  source = "./modules/databricks"

  resource_group_name = azurerm_resource_group.data_platform.name
  location           = var.location
  naming_prefix      = local.naming_prefix
  tags               = local.common_tags
  
  # Databricks Configuration
  sku                    = var.databricks_sku
  managed_resource_group = "${local.naming_prefix}-databricks-managed-rg"
  
  # Network Integration
  virtual_network_id              = module.networking.vnet_id
  private_subnet_name             = module.networking.databricks_private_subnet_name
  public_subnet_name              = module.networking.databricks_public_subnet_name
  private_subnet_network_security_group_association_id = module.networking.databricks_private_nsg_association_id
  public_subnet_network_security_group_association_id  = module.networking.databricks_public_nsg_association_id
  
  # Storage Integration
  storage_account_id = module.data_lake.storage_account_id
  
  # Security
  key_vault_id = module.security.key_vault_id
}

module "data_factory" {
  source = "./modules/data-factory"

  resource_group_name = azurerm_resource_group.data_platform.name
  location           = var.location
  naming_prefix      = local.naming_prefix
  tags               = local.common_tags
  
  # Data Factory Configuration
  github_configuration = var.adf_github_config
  
  # Integration Runtimes
  enable_azure_ir     = true
  enable_self_hosted_ir = var.enable_self_hosted_ir
  
  # Network Integration
  subnet_id = module.networking.private_endpoint_subnet_id
  
  # Linked Services
  storage_account_id = module.data_lake.storage_account_id
  databricks_workspace_url = module.databricks.workspace_url
  key_vault_id = module.security.key_vault_id
}

module "purview" {
  source = "./modules/purview"

  resource_group_name = azurerm_resource_group.data_platform.name
  location           = var.location
  naming_prefix      = local.naming_prefix
  tags               = local.common_tags
  
  # Purview Configuration
  sku = var.purview_sku
  
  # Data Sources
  storage_account_id = module.data_lake.storage_account_id
  databricks_workspace_id = module.databricks.workspace_id
  
  # Security
  key_vault_id = module.security.key_vault_id
}

module "monitoring" {
  source = "./modules/monitoring"

  resource_group_name = azurerm_resource_group.monitoring.name
  location           = var.location
  naming_prefix      = local.naming_prefix
  tags               = local.common_tags
  
  # Log Analytics
  log_retention_days = var.log_retention_days
  
  # Application Insights
  application_type = "web"
  
  # Monitored Resources
  monitored_resources = {
    storage_account     = module.data_lake.storage_account_id
    databricks_workspace = module.databricks.workspace_id
    data_factory       = module.data_factory.data_factory_id
    key_vault         = module.security.key_vault_id
  }
  
  # Alerting
  notification_email = var.notification_email
  enable_automated_remediation = var.enable_automated_remediation
}

module "automation" {
  source = "./modules/automation"

  resource_group_name = azurerm_resource_group.data_platform.name
  location           = var.location
  naming_prefix      = local.naming_prefix
  tags               = local.common_tags
  
  # Function Apps for Self-Healing
  function_apps = var.automation_functions
  
  # Logic Apps for Orchestration
  logic_apps = var.logic_app_workflows
  
  # Event Grid for Event-Driven Architecture
  event_grid_topics = var.event_grid_topics
  
  # Integration
  storage_account_id = module.data_lake.storage_account_id
  log_analytics_workspace_id = module.monitoring.log_analytics_workspace_id
  key_vault_id = module.security.key_vault_id
}
