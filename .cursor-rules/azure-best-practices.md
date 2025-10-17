# Azure Cloud Services Best Practices

## Authentication and Authorization

### Managed Identities
- Use managed identities over service principals when possible
- System-assigned for single-resource scenarios
- User-assigned for multiple resources
- No credential management required

### Service Principals
- Use only when managed identities aren't available
- Store credentials in Azure Key Vault
- Rotate credentials regularly
- Apply principle of least privilege

### RBAC
- Use built-in roles when possible
- Create custom roles for specific needs
- Assign roles at appropriate scope (subscription, resource group, resource)
- Regular access reviews

## Resource Management

### Resource Naming
- Follow Azure naming conventions
- Use consistent naming patterns
- Include environment in names (dev, staging, prod)
- Use abbreviations from Microsoft documentation

### Tagging Strategy
```
Environment: dev/staging/prod
Owner: team-name
CostCenter: cost-center-id
Application: app-name
ManagedBy: terraform/manual/arm
```

### Resource Organization
- Use resource groups logically (by application, environment, or lifecycle)
- Apply locks on critical resources (delete lock)
- Use management groups for enterprise governance
- Implement Azure Policy for compliance

## Networking

### Virtual Networks
- Plan IP address space carefully
- Use network security groups (NSGs)
- Implement Azure Firewall for centralized protection
- Use private endpoints for PaaS services

### Connectivity
- Use Azure VPN Gateway for hybrid connectivity
- Implement ExpressRoute for dedicated connections
- Use VNet peering for inter-VNet communication
- Apply service endpoints where appropriate

## Storage

### Blob Storage
- Use appropriate access tiers (Hot, Cool, Archive)
- Implement lifecycle management policies
- Enable soft delete for protection
- Use private endpoints for secure access

### Storage Account Security
- Disable public access when not needed
- Use SAS tokens with minimal permissions
- Enable storage analytics and logging
- Implement Azure Storage firewalls

## Compute

### Virtual Machines
- Use availability zones for high availability
- Implement VM scale sets for scalability
- Use managed disks
- Enable Azure Backup

### Azure Kubernetes Service (AKS)
- Use system node pools for system pods
- Implement network policies
- Use Azure CNI for advanced networking
- Enable cluster autoscaler
- Use workload identity for pod authentication

### App Service
- Use deployment slots for staging
- Enable auto-scaling
- Implement Application Insights
- Use managed certificates

## Monitoring and Diagnostics

### Azure Monitor
- Enable diagnostic settings for all resources
- Send logs to Log Analytics workspace
- Create action groups for alerting
- Use workbooks for visualization

### Application Insights
- Instrument applications for telemetry
- Track dependencies
- Monitor availability with web tests
- Set up smart detection

### Log Analytics
- Create KQL queries for insights
- Set up log retention policies
- Use Log Analytics workspaces per environment
- Implement query-based alerts

## Cost Management

### Cost Optimization
- Use Azure Advisor recommendations
- Implement auto-shutdown for dev/test VMs
- Right-size resources based on metrics
- Use Azure Hybrid Benefit for licensing
- Reserve capacity for predictable workloads

### Cost Monitoring
- Set up budgets with alerts
- Use cost analysis for insights
- Tag resources for cost allocation
- Review and optimize regularly

## Security

### Azure Security Center / Defender
- Enable Microsoft Defender for Cloud
- Implement security recommendations
- Monitor security score
- Enable just-in-time VM access

### Key Vault
- Store all secrets, keys, and certificates
- Enable soft delete and purge protection
- Use separate vaults per environment
- Implement access policies or RBAC

### Network Security
- Implement DDoS protection
- Use Azure Front Door for global applications
- Enable Azure Firewall threat intelligence
- Implement Web Application Firewall (WAF)

## Backup and Disaster Recovery

### Backup Strategy
- Use Azure Backup for VMs
- Enable geo-redundant storage (GRS)
- Test restore procedures regularly
- Document backup policies

### Site Recovery
- Use Azure Site Recovery for DR
- Define recovery plans
- Test failover scenarios
- Document RTO and RPO

## Compliance and Governance

### Azure Policy
- Define policies for resource compliance
- Use policy initiatives for grouped requirements
- Monitor compliance dashboard
- Remediate non-compliant resources

### Blueprints
- Create blueprints for standard environments
- Version blueprints for tracking
- Assign blueprints at appropriate scope
- Update assignments as needed

## Regional Considerations

### Region Selection
- Consider data residency requirements
- Check service availability per region
- Plan for regional outages
- Use paired regions for DR

### Multi-Region Architecture
- Use Traffic Manager for global routing
- Implement geo-replication for data
- Consider latency requirements
- Plan for region failover

## CLI and PowerShell Best Practices

### Azure CLI
```bash
# Use --output for structured data
az resource list --output table

# Use --query for filtering
az vm list --query "[?powerState=='VM running']"

# Use resource IDs for unambiguous operations
az vm show --ids /subscriptions/.../resourceGroups/.../providers/Microsoft.Compute/virtualMachines/vm-name
```

### Azure PowerShell
```powershell
# Use proper error handling
try {
    Get-AzResource -Name "resource-name" -ErrorAction Stop
} catch {
    Write-Error "Failed to get resource: $_"
}

# Use splatting for readable parameters
$params = @{
    ResourceGroupName = "rg-name"
    Location = "eastus"
    Name = "resource-name"
}
New-AzResourceGroup @params
```

