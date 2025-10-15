output "private_link_service_id" {
  description = "The ID of the Private Link Service"
  value       = azurerm_private_link_service.pls.id
}

output "private_link_service_alias" {
  description = "The alias of the Private Link Service (used for creating Private Endpoints)"
  value       = azurerm_private_link_service.pls.alias
}

output "private_link_service_name" {
  description = "The name of the Private Link Service"
  value       = azurerm_private_link_service.pls.name
}

output "pls_subnet_id" {
  description = "The ID of the subnet used for Private Link Service"
  value       = local.pls_subnet_id
}

output "network_security_group_id" {
  description = "The ID of the Network Security Group (if created)"
  value       = var.create_nsg ? azurerm_network_security_group.pls_nsg[0].id : null
}

output "aks_node_resource_group" {
  description = "The node resource group of the AKS cluster"
  value       = data.azurerm_resource_group.aks_node_rg.name
}

output "private_link_service_nat_ips" {
  description = "The NAT IP addresses of the Private Link Service"
  value       = azurerm_private_link_service.pls.nat_ip_configuration
}

