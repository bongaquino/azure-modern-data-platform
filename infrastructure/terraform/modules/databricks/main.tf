# Databricks Module for Modern Data Platform
# Implements automated, self-healing Databricks workspace with Unity Catalog

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.30"
    }
  }
}

# Databricks Workspace
resource "azurerm_databricks_workspace" "main" {
  name                = "${var.naming_prefix}-databricks"
  resource_group_name = var.resource_group_name
  location           = var.location
  sku                = var.sku

  # Network configuration for secure deployment
  custom_parameters {
    no_public_ip                                         = true
    virtual_network_id                                   = var.virtual_network_id
    private_subnet_name                                  = var.private_subnet_name
    public_subnet_name                                   = var.public_subnet_name
    private_subnet_network_security_group_association_id = var.private_subnet_network_security_group_association_id
    public_subnet_network_security_group_association_id  = var.public_subnet_network_security_group_association_id
    
    # Storage account configuration
    storage_account_name = "${replace(var.naming_prefix, "-", "")}dbfs"
    storage_account_sku_name = "Standard_LRS"
  }

  managed_resource_group_name = var.managed_resource_group

  tags = merge(var.tags, {
    Component = "Databricks"
    Purpose   = "Data Processing"
    Security  = "VNet-Integrated"
  })

  lifecycle {
    ignore_changes = [
      custom_parameters[0].storage_account_name
    ]
  }
}

# Configure Databricks provider for workspace configuration
provider "databricks" {
  azure_workspace_resource_id = azurerm_databricks_workspace.main.id
}

# Unity Catalog Metastore (if not exists)
resource "databricks_metastore" "unity_catalog" {
  count = var.enable_unity_catalog ? 1 : 0
  
  name          = "${var.naming_prefix}-unity-metastore"
  storage_root  = "abfss://unity-catalog@${var.unity_catalog_storage_account}.dfs.core.windows.net/"
  region        = var.location
  
  force_destroy = var.environment == "dev" ? true : false

  depends_on = [azurerm_databricks_workspace.main]
}

# Assign metastore to workspace
resource "databricks_metastore_assignment" "workspace" {
  count = var.enable_unity_catalog ? 1 : 0
  
  workspace_id = azurerm_databricks_workspace.main.workspace_id
  metastore_id = databricks_metastore.unity_catalog[0].id

  depends_on = [databricks_metastore.unity_catalog]
}

# Create automated clusters for different workloads
resource "databricks_cluster" "data_engineering" {
  cluster_name  = "${var.naming_prefix}-data-engineering"
  spark_version = var.spark_version
  node_type_id  = var.node_type_id
  
  # Autoscaling configuration
  autoscale {
    min_workers = var.auto_scale_min_workers
    max_workers = var.auto_scale_max_workers
  }

  # Auto-termination for cost optimization
  autotermination_minutes = var.auto_termination_minutes

  # Cluster configuration
  driver_node_type_id = var.driver_node_type_id
  
  # Enable automatic cluster restart
  enable_elastic_disk = true
  
  # Spark configuration for optimization
  spark_conf = {
    "spark.databricks.cluster.profile"                    = "singleNode"
    "spark.databricks.delta.preview.enabled"              = "true"
    "spark.databricks.delta.retentionDurationCheck.enabled" = "false"
    "spark.sql.adaptive.enabled"                          = "true"
    "spark.sql.adaptive.coalescePartitions.enabled"       = "true"
    "spark.sql.adaptive.localShuffleReader.enabled"       = "true"
    "spark.sql.adaptive.skewJoin.enabled"                 = "true"
  }

  # Custom tags
  custom_tags = merge(var.tags, {
    ClusterType = "DataEngineering"
    AutoScale   = "Enabled"
    WorkloadType = "Batch"
  })

  # Library installations
  library {
    pypi {
      package = "azure-storage-blob"
    }
  }

  library {
    pypi {
      package = "azure-identity"
    }
  }

  library {
    pypi {
      package = "great-expectations"
    }
  }

  depends_on = [azurerm_databricks_workspace.main]
}

# High-concurrency cluster for analytics workloads
resource "databricks_cluster" "analytics" {
  cluster_name  = "${var.naming_prefix}-analytics"
  spark_version = var.spark_version
  node_type_id  = var.analytics_node_type_id
  
  # High concurrency configuration
  num_workers = var.analytics_num_workers
  
  # Enable table access control
  data_security_mode = "USER_ISOLATION"
  
  # Auto-termination
  autotermination_minutes = var.auto_termination_minutes

  # Spark configuration for analytics
  spark_conf = {
    "spark.databricks.cluster.profile"                = "serverless"
    "spark.databricks.repl.allowedLanguages"          = "python,sql,scala,r"
    "spark.databricks.delta.preview.enabled"          = "true"
    "spark.sql.adaptive.enabled"                      = "true"
    "spark.sql.adaptive.coalescePartitions.enabled"   = "true"
  }

  custom_tags = merge(var.tags, {
    ClusterType = "Analytics"
    Concurrency = "High"
    WorkloadType = "Interactive"
  })

  depends_on = [azurerm_databricks_workspace.main]
}

# MLOps cluster for machine learning workloads
resource "databricks_cluster" "mlops" {
  count = var.enable_mlops_cluster ? 1 : 0
  
  cluster_name  = "${var.naming_prefix}-mlops"
  spark_version = var.ml_spark_version
  node_type_id  = var.ml_node_type_id
  
  autoscale {
    min_workers = 1
    max_workers = var.ml_max_workers
  }

  autotermination_minutes = var.auto_termination_minutes

  spark_conf = {
    "spark.databricks.cluster.profile"              = "singleNode"
    "spark.databricks.delta.preview.enabled"        = "true"
    "spark.databricks.mlflow.trackingStore.enabled" = "true"
  }

  custom_tags = merge(var.tags, {
    ClusterType = "MLOps"
    Purpose     = "MachineLearning"
    MLFlow      = "Enabled"
  })

  # ML-specific libraries
  library {
    pypi {
      package = "mlflow"
    }
  }

  library {
    pypi {
      package = "scikit-learn"
    }
  }

  library {
    pypi {
      package = "pandas"
    }
  }

  library {
    pypi {
      package = "numpy"
    }
  }

  depends_on = [azurerm_databricks_workspace.main]
}

# Secret scopes for secure credential management
resource "databricks_secret_scope" "key_vault" {
  name = "key-vault-secrets"

  keyvault_metadata {
    resource_id = var.key_vault_id
    dns_name    = var.key_vault_dns_name
  }

  depends_on = [azurerm_databricks_workspace.main]
}

# Workspace configuration
resource "databricks_workspace_conf" "main" {
  custom_config = {
    "enableIpAccessLists"                    = "true"
    "enableTokensConfig"                     = "true"
    "enableDeprecatedClusterNamedInitScripts" = "false"
    "enableDeprecatedGlobalInitScripts"      = "false"
    "enableWebTerminal"                      = "true"
    "maxTokenLifetimeDays"                   = "90"
    "storeInteractiveNotebookResultsInCustomerAccount" = "true"
  }

  depends_on = [azurerm_databricks_workspace.main]
}

# Automated jobs for data processing
resource "databricks_job" "data_quality_check" {
  name = "${var.naming_prefix}-data-quality-check"

  new_cluster {
    spark_version = var.spark_version
    node_type_id  = var.node_type_id
    num_workers   = 2
    
    spark_conf = {
      "spark.databricks.delta.preview.enabled" = "true"
    }
  }

  notebook_task {
    notebook_path = "/Shared/automation/data-quality-check"
  }

  schedule {
    quartz_cron_expression = "0 0 2 * * ?"  # Daily at 2 AM
    timezone_id           = "America/New_York"
    pause_status          = "UNPAUSED"
  }

  email_notifications {
    on_failure = [var.notification_email]
    on_success = []
  }

  tags = merge(var.tags, {
    JobType = "DataQuality"
    Schedule = "Daily"
    Automated = "True"
  })

  depends_on = [azurerm_databricks_workspace.main]
}

# Repository for collaborative development
resource "databricks_repo" "data_platform" {
  count = var.git_repo_url != null ? 1 : 0
  
  url      = var.git_repo_url
  provider = "gitHub"  # or "azureDevOpsServices"
  path     = "/Repos/Shared/data-platform"

  depends_on = [azurerm_databricks_workspace.main]
}
