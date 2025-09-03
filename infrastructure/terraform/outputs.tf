# Outputs for Azure Modern Data Platform
# Provides essential resource information for dependent systems and modules

# Resource Group Outputs
output "resource_groups" {
  description = "Information about created resource groups"
  value = {
    data_platform = {
      id       = azurerm_resource_group.data_platform.id
      name     = azurerm_resource_group.data_platform.name
      location = azurerm_resource_group.data_platform.location
    }
    networking = {
      id       = azurerm_resource_group.networking.id
      name     = azurerm_resource_group.networking.name
      location = azurerm_resource_group.networking.location
    }
    security = {
      id       = azurerm_resource_group.security.id
      name     = azurerm_resource_group.security.name
      location = azurerm_resource_group.security.location
    }
    monitoring = {
      id       = azurerm_resource_group.monitoring.id
      name     = azurerm_resource_group.monitoring.name
      location = azurerm_resource_group.monitoring.location
    }
  }
}

# Networking Outputs
output "networking" {
  description = "Networking infrastructure details"
  value = {
    vnet_id                = module.networking.vnet_id
    vnet_name              = module.networking.vnet_name
    private_endpoint_subnet_id = module.networking.private_endpoint_subnet_id
    databricks_private_subnet_id = module.networking.databricks_private_subnet_id
    databricks_public_subnet_id  = module.networking.databricks_public_subnet_id
    nsg_ids = module.networking.nsg_ids
  }
  sensitive = false
}

# Security Outputs
output "security" {
  description = "Security infrastructure details"
  value = {
    key_vault_id   = module.security.key_vault_id
    key_vault_uri  = module.security.key_vault_uri
    key_vault_name = module.security.key_vault_name
  }
  sensitive = false
}

# Data Lake Outputs
output "data_lake" {
  description = "Data Lake storage details"
  value = {
    storage_account_id               = module.data_lake.storage_account_id
    storage_account_name             = module.data_lake.storage_account_name
    storage_account_primary_endpoint = module.data_lake.storage_account_primary_endpoint
    storage_account_primary_dfs_endpoint = module.data_lake.storage_account_primary_dfs_endpoint
    containers = module.data_lake.containers
  }
  sensitive = false
}

# Databricks Outputs
output "databricks" {
  description = "Databricks workspace details"
  value = {
    workspace_id               = module.databricks.workspace_id
    workspace_url             = module.databricks.workspace_url
    workspace_name            = module.databricks.workspace_name
    managed_resource_group_id = module.databricks.managed_resource_group_id
  }
  sensitive = false
}

# Data Factory Outputs
output "data_factory" {
  description = "Azure Data Factory details"
  value = {
    data_factory_id       = module.data_factory.data_factory_id
    data_factory_name     = module.data_factory.data_factory_name
    integration_runtime_names = module.data_factory.integration_runtime_names
    linked_service_names  = module.data_factory.linked_service_names
  }
  sensitive = false
}

# Purview Outputs
output "purview" {
  description = "Microsoft Purview details"
  value = {
    purview_account_id       = module.purview.purview_account_id
    purview_account_name     = module.purview.purview_account_name
    catalog_endpoint         = module.purview.catalog_endpoint
    guardian_endpoint        = module.purview.guardian_endpoint
    scan_endpoint           = module.purview.scan_endpoint
  }
  sensitive = false
}

# Monitoring Outputs
output "monitoring" {
  description = "Monitoring and observability details"
  value = {
    log_analytics_workspace_id   = module.monitoring.log_analytics_workspace_id
    log_analytics_workspace_name = module.monitoring.log_analytics_workspace_name
    application_insights_id      = module.monitoring.application_insights_id
    application_insights_name    = module.monitoring.application_insights_name
    instrumentation_key         = module.monitoring.instrumentation_key
    action_group_ids           = module.monitoring.action_group_ids
  }
  sensitive = true
}

# Automation Outputs
output "automation" {
  description = "Automation infrastructure details"
  value = {
    function_app_ids        = module.automation.function_app_ids
    function_app_names      = module.automation.function_app_names
    logic_app_ids          = module.automation.logic_app_ids
    logic_app_names        = module.automation.logic_app_names
    event_grid_topic_ids   = module.automation.event_grid_topic_ids
    event_grid_topic_names = module.automation.event_grid_topic_names
  }
  sensitive = false
}

# Connection Strings and Endpoints (Sensitive)
output "connection_details" {
  description = "Connection strings and sensitive endpoints"
  value = {
    storage_connection_string = module.data_lake.storage_connection_string
    databricks_host          = module.databricks.workspace_url
    data_factory_endpoint    = module.data_factory.data_factory_endpoint
    key_vault_uri           = module.security.key_vault_uri
    log_analytics_workspace_key = module.monitoring.log_analytics_workspace_key
  }
  sensitive = true
}

# Deployment Information
output "deployment_info" {
  description = "Information about the deployment"
  value = {
    environment        = var.environment
    project_name      = var.project_name
    location          = var.location
    naming_prefix     = local.naming_prefix
    deployment_time   = timestamp()
    terraform_version = ">=1.0"
    common_tags       = local.common_tags
  }
}

# Service Principal Information (for CI/CD)
output "service_principal_info" {
  description = "Service principal information for automation"
  value = {
    tenant_id           = data.azurerm_client_config.current.tenant_id
    subscription_id     = data.azurerm_client_config.current.subscription_id
    resource_group_names = {
      data_platform = azurerm_resource_group.data_platform.name
      networking    = azurerm_resource_group.networking.name
      security      = azurerm_resource_group.security.name
      monitoring    = azurerm_resource_group.monitoring.name
    }
  }
  sensitive = false
}

# Data Platform Endpoints Summary
output "data_platform_endpoints" {
  description = "Summary of all data platform endpoints"
  value = {
    storage_dfs_endpoint     = module.data_lake.storage_account_primary_dfs_endpoint
    databricks_workspace    = module.databricks.workspace_url
    data_factory_portal     = "https://adf.azure.com/en/home?factory=${module.data_factory.data_factory_name}"
    purview_portal         = "https://web.purview.azure.com/resource/${module.purview.purview_account_name}"
    key_vault_portal       = "https://portal.azure.com/#@${data.azurerm_client_config.current.tenant_id}/resource${module.security.key_vault_id}"
    monitoring_portal      = "https://portal.azure.com/#@${data.azurerm_client_config.current.tenant_id}/resource${module.monitoring.log_analytics_workspace_id}"
  }
}

# Cost Management Tags for Resource Tracking
output "cost_tracking" {
  description = "Cost tracking and resource tagging information"
  value = {
    cost_center     = var.cost_center
    environment     = var.environment
    project_name    = var.project_name
    owner          = var.owner
    resource_count = {
      resource_groups = 4
      storage_accounts = 1
      databricks_workspaces = 1
      data_factories = 1
      purview_accounts = 1
      key_vaults = 1
      function_apps = length(var.automation_functions)
      logic_apps = length(var.logic_app_workflows)
    }
  }
}
