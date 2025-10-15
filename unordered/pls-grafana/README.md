# Grafana Private Link Service Terraform Module

This module creates a Kubernetes Service with Internal Load Balancer and an Azure Private Link Service for Grafana, ensuring persistency and reproducibility.

## Features

- ✅ Kubernetes Service with Internal Load Balancer
- ✅ Azure Private Link Service automatically created
- ✅ Idempotent - can be recreated anytime
- ✅ Proper dependency management
- ✅ State tracked in Terraform

## Usage

```hcl
module "grafana_pls" {
  source = "./modules/grafana-pls"
  
  # Required
  node_resource_group = "MC_rg-observability-aks_aks-observability_westus2"
  pls_subnet_id       = data.azurerm_subnet.aks_subnet.id
  
  # Optional
  service_name        = "grafana-internal"
  namespace           = "grafana-test"
  pls_name            = "pls-grafana-observability"
  load_balancer_ip    = "10.224.0.28"  # Optional static IP
  
  pod_selector = {
    app = "grafana"
  }
  
  # PLS Access Control
  visibility_subscriptions = [
    "00e10e35-0ad0-427e-893a-72f3b42387c1",  # DAP_DevOps
    "cda76fc5-a3ee-4c98-b4ba-055125b3de93"   # DAP_Dev
  ]
  
  environment = "production"
}
```

## Outputs

- `service_name` - Kubernetes service name
- `load_balancer_ip` - Internal load balancer IP
- `pls_alias` - Private Link Service alias (share with consumers)
- `pls_id` - Private Link Service resource ID

## Benefits of IaC Approach

### 1. **Persistency**
- Configuration stored in Git
- Can be recreated anytime
- Version controlled

### 2. **Consistency**
- Same configuration across environments
- No manual errors
- Documented dependencies

### 3. **Disaster Recovery**
- Delete and recreate entire stack
- Terraform handles proper order
- No orphaned resources

## Example: Complete Setup

```hcl
# File: terraform-k8s-setup/grafana-pls-prod.tf

# Get existing resources
data "azurerm_subnet" "aks_subnet" {
  name                 = "aks-subnet"
  virtual_network_name = "aks-vnet-38705521"
  resource_group_name  = "MC_rg-observability-aks_aks-observability_westus2"
}

# Create Grafana PLS
module "grafana_pls" {
  source = "./modules/grafana-pls"
  
  service_name        = "grafana"
  namespace           = "grafana-test"
  pls_name            = "pls-grafana-prod"
  node_resource_group = "MC_rg-observability-aks_aks-observability_westus2"
  pls_subnet_id       = data.azurerm_subnet.aks_subnet.id
  
  pod_selector = {
    app = "grafana"
  }
  
  visibility_subscriptions = [
    "00e10e35-0ad0-427e-893a-72f3b42387c1"
  ]
}

# Output the PLS alias
output "grafana_pls_alias" {
  value       = module.grafana_pls.pls_alias
  description = "Share this alias with consumers"
}
```

## How to Use

### Initialize and Apply

```bash
cd terraform-k8s-setup

# Initialize Terraform
terraform init

# Plan changes
terraform plan

# Apply configuration
terraform apply
```

### Recreate After Deletion

If someone deletes the Kubernetes service:

```bash
# Simply reapply
terraform apply

# Terraform will:
# 1. Detect the service is missing
# 2. Recreate the service
# 3. Wait for load balancer
# 4. Recreate the PLS
# 5. Everything back to desired state!
```

## State Management

### Using Remote State (Recommended)

```hcl
# backend.tf
terraform {
  backend "azurerm" {
    resource_group_name  = "terraform-state-rg"
    storage_account_name = "tfstatedapdevops"
    container_name       = "tfstate"
    key                  = "grafana-pls.tfstate"
  }
}
```

Benefits:
- ✅ State stored in Azure Storage
- ✅ Team collaboration
- ✅ State locking
- ✅ Disaster recovery

## Monitoring

Add monitoring to track PLS health:

```hcl
resource "azurerm_monitor_metric_alert" "pls_connections" {
  name                = "pls-grafana-low-connections"
  resource_group_name = var.node_resource_group
  scopes              = [azurerm_private_link_service.grafana_pls.id]
  
  criteria {
    metric_namespace = "Microsoft.Network/privateLinkServices"
    metric_name      = "BytesInDDoS"
    aggregation      = "Total"
    operator         = "LessThan"
    threshold        = 1
  }
  
  action {
    action_group_id = var.alert_action_group_id
  }
}
```

## Troubleshooting

### Issue: Frontend IP Not Found

**Error**: `Cannot find load balancer frontend IP`

**Solution**: Increase wait time
```hcl
resource "time_sleep" "wait_for_lb" {
  create_duration = "120s"  # Increase from 60s
}
```

### Issue: PLS Creation Fails

**Error**: `Private Link Service network policies not disabled`

**Solution**: Ensure subnet has policies disabled
```bash
az network vnet subnet update \
  --resource-group MC_rg-observability-aks_aks-observability_westus2 \
  --vnet-name aks-vnet-38705521 \
  --name aks-subnet \
  --disable-private-link-service-network-policies true
```

## Clean Up

```bash
# Destroy everything
terraform destroy

# This will:
# 1. Delete PLS
# 2. Delete Kubernetes service
# 3. Clean up load balancer
```


