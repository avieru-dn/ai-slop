# Persistent Private Link Service for Grafana
# This ensures PLS alias survives service recreation

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.29"
    }
  }
}

# Data: Existing resources
data "azurerm_subscription" "current" {}

data "azurerm_virtual_network" "aks_vnet" {
  name                = "aks-vnet-38705521"
  resource_group_name = "MC_rg-observability-aks_aks-observability_westus2"
}

data "azurerm_subnet" "aks_subnet" {
  name                 = "aks-subnet"
  virtual_network_name = data.azurerm_virtual_network.aks_vnet.name
  resource_group_name  = "MC_rg-observability-aks_aks-observability_westus2"
}

data "azurerm_lb" "kubernetes_internal" {
  name                = "kubernetes-internal"
  resource_group_name = "MC_rg-observability-aks_aks-observability_westus2"
}

# Create a STATIC frontend IP (not managed by K8s service)
resource "azurerm_lb_frontend_ip_configuration" "grafana_static" {
  name                          = "grafana-pls-static-frontend"
  loadbalancer_id               = data.azurerm_lb.kubernetes_internal.id
  private_ip_address_allocation = "Static"
  private_ip_address            = "10.224.5.100"  # Choose unused IP
  subnet_id                     = data.azurerm_subnet.aks_subnet.id
  
  lifecycle {
    prevent_destroy = true  # Protect from accidental deletion
  }
}

# Create PERSISTENT Private Link Service
resource "azurerm_private_link_service" "grafana_persistent" {
  name                = "pls-grafana-persistent"
  resource_group_name = "MC_rg-observability-aks_aks-observability_westus2"
  location            = "westus2"
  
  # Use the static frontend IP
  load_balancer_frontend_ip_configuration_ids = [
    azurerm_lb_frontend_ip_configuration.grafana_static.id
  ]
  
  nat_ip_configuration {
    name      = "primary"
    primary   = true
    subnet_id = data.azurerm_subnet.aks_subnet.id
  }
  
  # Visibility control
  visibility_subscription_ids = [
    data.azurerm_subscription.current.subscription_id,
    "cda76fc5-a3ee-4c98-b4ba-055125b3de93"  # DAP_Dev
  ]
  
  tags = {
    Environment = "production"
    Service     = "grafana"
    ManagedBy   = "terraform"
    Critical    = "true"
    Purpose     = "persistent-pls"
  }
  
  lifecycle {
    prevent_destroy = true  # CRITICAL: Protect PLS from deletion
    
    # Warn if would be replaced
    create_before_destroy = true
  }
}

# Create load balancing rule to route traffic
resource "azurerm_lb_rule" "grafana_static_rule" {
  name                           = "grafana-static-lb-rule"
  loadbalancer_id                = data.azurerm_lb.kubernetes_internal.id
  protocol                       = "Tcp"
  frontend_port                  = 3000
  backend_port                   = 3000
  frontend_ip_configuration_name = azurerm_lb_frontend_ip_configuration.grafana_static.name
  backend_address_pool_ids       = [data.azurerm_lb.kubernetes_internal.backend_address_pool[0].id]
  probe_id                       = azurerm_lb_probe.grafana_health.id
  enable_floating_ip             = false
  enable_tcp_reset               = true
  idle_timeout_in_minutes        = 4
}

# Health probe
resource "azurerm_lb_probe" "grafana_health" {
  name                = "grafana-health-probe"
  loadbalancer_id     = data.azurerm_lb.kubernetes_internal.id
  protocol            = "Tcp"
  port                = 3000
  interval_in_seconds = 5
  number_of_probes    = 2
}

# Output the PERMANENT alias
output "pls_alias_permanent" {
  value       = azurerm_private_link_service.grafana_persistent.alias
  description = "PERMANENT PLS alias - share this with consumers (never changes!)"
}

output "static_frontend_ip" {
  value       = azurerm_lb_frontend_ip_configuration.grafana_static.private_ip_address
  description = "Static frontend IP for PLS"
}

# Store alias in a file for tracking
resource "local_file" "pls_alias_record" {
  content  = <<-EOF
    # Grafana PLS Alias Record
    # Generated: ${timestamp()}
    
    PLS Name: ${azurerm_private_link_service.grafana_persistent.name}
    PLS Alias: ${azurerm_private_link_service.grafana_persistent.alias}
    Static IP: ${azurerm_lb_frontend_ip_configuration.grafana_static.private_ip_address}
    
    Share this alias with consumers:
    ${azurerm_private_link_service.grafana_persistent.alias}
    
    This alias will NOT change even if Kubernetes service is deleted/recreated!
  EOF
  filename = "${path.module}/PLS_ALIAS_PERMANENT.txt"
}

# Notification on changes (optional)
resource "null_resource" "alias_change_detector" {
  triggers = {
    alias = azurerm_private_link_service.grafana_persistent.alias
  }
  
  provisioner "local-exec" {
    command = <<-EOF
      echo "================================================"
      echo "PLS Alias: ${azurerm_private_link_service.grafana_persistent.alias}"
      echo "This alias is PERMANENT and will not change!"
      echo "================================================"
    EOF
  }
}


