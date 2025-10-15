# Grafana Internal Service with Private Link Service
# This ensures the PLS is recreated if the service is deleted

terraform {
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.29"
    }
  }
}

# Kubernetes Service with Internal Load Balancer
resource "kubernetes_service" "grafana_internal" {
  metadata {
    name      = var.service_name
    namespace = var.namespace
    
    annotations = {
      "service.beta.kubernetes.io/azure-load-balancer-internal" = "true"
    }
    
    labels = {
      app       = "grafana"
      component = "observability"
      managedBy = "terraform"
    }
  }
  
  spec {
    type = "LoadBalancer"
    
    # Optional: Specify static IP
    load_balancer_ip = var.load_balancer_ip
    
    session_affinity = "ClientIP"
    
    port {
      name        = "web"
      protocol    = "TCP"
      port        = 3000
      target_port = 3000
    }
    
    selector = var.pod_selector
  }
  
  # Wait for load balancer to be provisioned
  timeouts {
    create = "10m"
  }
}

# Wait for the load balancer IP to be assigned
resource "time_sleep" "wait_for_lb" {
  depends_on = [kubernetes_service.grafana_internal]
  
  create_duration = "60s"
}

# Get the load balancer details
data "azurerm_lb" "kubernetes_internal" {
  depends_on = [time_sleep.wait_for_lb]
  
  name                = "kubernetes-internal"
  resource_group_name = var.node_resource_group
}

# Get the frontend IP configuration for the service
data "azurerm_lb_frontend_ip_configuration" "grafana_frontend" {
  depends_on = [time_sleep.wait_for_lb]
  
  name            = local.frontend_ip_name
  loadbalancer_id = data.azurerm_lb.kubernetes_internal.id
}

# Private Link Service
resource "azurerm_private_link_service" "grafana_pls" {
  depends_on = [
    kubernetes_service.grafana_internal,
    time_sleep.wait_for_lb
  ]
  
  name                = var.pls_name
  resource_group_name = var.node_resource_group
  location            = var.location
  
  # Connect to the load balancer frontend
  load_balancer_frontend_ip_configuration_ids = [
    data.azurerm_lb_frontend_ip_configuration.grafana_frontend.id
  ]
  
  # NAT IP configuration
  nat_ip_configuration {
    name      = "primary"
    primary   = true
    subnet_id = var.pls_subnet_id
  }
  
  # Visibility and approval settings
  visibility_subscription_ids = var.visibility_subscriptions
  auto_approval_subscription_ids = var.auto_approval_subscriptions
  
  tags = {
    Environment = var.environment
    Service     = "grafana"
    ManagedBy   = "terraform"
    Purpose     = "private-link"
  }
}

# Helper local to get the frontend IP name from service UID
locals {
  # The frontend IP name is based on the service UID
  # Format: a<service-uid-without-dashes>-TCP-<port>
  service_uid_clean = replace(kubernetes_service.grafana_internal.metadata[0].uid, "-", "")
  frontend_ip_name  = "a${substr(local.service_uid_clean, 0, 32)}-TCP-3000"
}


