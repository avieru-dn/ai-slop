variable "service_name" {
  description = "Name of the Kubernetes service"
  type        = string
  default     = "grafana-internal"
}

variable "namespace" {
  description = "Kubernetes namespace"
  type        = string
  default     = "monitoring"
}

variable "pod_selector" {
  description = "Selector labels for pods"
  type        = map(string)
  default = {
    "app.kubernetes.io/name" = "grafana"
  }
}

variable "load_balancer_ip" {
  description = "Static IP for load balancer (optional)"
  type        = string
  default     = null
}

variable "pls_name" {
  description = "Name of the Private Link Service"
  type        = string
  default     = "pls-grafana-observability"
}

variable "node_resource_group" {
  description = "AKS node resource group (MC_* resource group)"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "westus2"
}

variable "pls_subnet_id" {
  description = "Subnet ID for Private Link Service NAT IPs"
  type        = string
}

variable "environment" {
  description = "Environment tag"
  type        = string
  default     = "production"
}

variable "visibility_subscriptions" {
  description = "List of subscription IDs that can see this PLS"
  type        = list(string)
  default     = []
}

variable "auto_approval_subscriptions" {
  description = "List of subscription IDs that are auto-approved"
  type        = list(string)
  default     = []
}


