# Azure Private Link Service (PLS) Setup Guide for AKS

This guide explains how to create and configure an Azure Private Link Service for services running in Azure Kubernetes Service (AKS).

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Architecture Overview](#architecture-overview)
3. [Method 1: Automatic PLS Creation via Kubernetes Annotations](#method-1-automatic-pls-creation-via-kubernetes-annotations)
4. [Method 2: Manual PLS Creation via Azure Portal](#method-2-manual-pls-creation-via-azure-portal)
5. [Method 3: Manual PLS Creation via Azure CLI](#method-3-manual-pls-creation-via-azure-cli)
6. [Method 4: Terraform/IaC Approach](#method-4-terraform-iac-approach)
7. [Verification and Testing](#verification-and-testing)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before creating a Private Link Service, ensure you have:

- ✅ An AKS cluster running and accessible
- ✅ A service you want to expose via Private Link
- ✅ A dedicated subnet for Private Link Service (separate from AKS nodes subnet)
- ✅ Appropriate Azure RBAC permissions:
  - `Network Contributor` on the VNet/subnet
  - `Contributor` on the AKS cluster
- ✅ Azure CLI installed (for CLI methods)
- ✅ `kubectl` configured to access your AKS cluster

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         AKS Cluster                         │
│                                                             │
│  ┌──────────────┐                                          │
│  │   Service    │  (type: LoadBalancer)                    │
│  │  (Grafana)   │                                          │
│  └──────┬───────┘                                          │
│         │                                                   │
│  ┌──────▼────────────────────────────┐                     │
│  │  Internal LoadBalancer             │                    │
│  │  (10.1.35.236)                    │                     │
│  └──────┬────────────────────────────┘                     │
└─────────┼──────────────────────────────────────────────────┘
          │
          │
┌─────────▼──────────────────────────────────────────────────┐
│         Private Link Service (PLS)                          │
│  Name: eos-oss-westus3-observ-grafana-pst-pls             │
│  Subnet: pls-subnet                                        │
│  Frontend IP: 10.1.35.236 (from LoadBalancer)             │
└─────────┬──────────────────────────────────────────────────┘
          │
          │ Private Endpoint Connection
          │
┌─────────▼──────────────────────────────────────────────────┐
│         Private Endpoint (Consumer Side)                    │
│  FQDN: *.azprv.3pc.att.com                                 │
│  Private IP: 10.x.x.x (in consumer VNet)                  │
└────────────────────────────────────────────────────────────┘
```

---

## Method 1: Automatic PLS Creation via Kubernetes Annotations

This is the **recommended and easiest method** - Kubernetes/Azure automatically creates and manages the PLS.

### Step 1: Prepare the Subnet (One-time setup)

Create a dedicated subnet for Private Link Service if you don't have one:

```bash
# Set variables
RESOURCE_GROUP="your-aks-rg"
VNET_NAME="your-aks-vnet"
PLS_SUBNET_NAME="pls-subnet"
PLS_SUBNET_PREFIX="10.1.100.0/24"  # Choose an available CIDR

# Create the subnet
az network vnet subnet create \
  --resource-group $RESOURCE_GROUP \
  --vnet-name $VNET_NAME \
  --name $PLS_SUBNET_NAME \
  --address-prefixes $PLS_SUBNET_PREFIX

# Disable private link service network policies (REQUIRED)
az network vnet subnet update \
  --resource-group $RESOURCE_GROUP \
  --vnet-name $VNET_NAME \
  --name $PLS_SUBNET_NAME \
  --disable-private-link-service-network-policies true
```

### Step 2: Configure Kubernetes Service with PLS Annotations

Create or update your service YAML or Helm values:

**Option A: Direct Kubernetes YAML**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: grafana
  namespace: grafana
  annotations:
    # Create internal LoadBalancer
    service.beta.kubernetes.io/azure-load-balancer-internal: "true"
    
    # Create Private Link Service
    service.beta.kubernetes.io/azure-pls-create: "true"
    service.beta.kubernetes.io/azure-pls-name: "my-app-pls"
    
    # Specify subnet for Private Link Service
    service.beta.kubernetes.io/azure-pls-ip-configuration-subnet: "pls-subnet"
    
    # Number of IP configs (usually 1 is sufficient)
    service.beta.kubernetes.io/azure-pls-ip-configuration-ip-address-count: "1"
    
    # Optional: Auto-approve Private Endpoint connections from these subscriptions
    # service.beta.kubernetes.io/azure-pls-auto-approval: "subscription-id-1,subscription-id-2"
    
    # Optional: Make Private Link Service visible to specific subscriptions
    # service.beta.kubernetes.io/azure-pls-visibility: "subscription-id-1,subscription-id-2"
    
    # Optional: Proxy protocol v2 (if your app supports it)
    # service.beta.kubernetes.io/azure-pls-proxy-protocol: "true"
spec:
  type: LoadBalancer
  loadBalancerIP: 10.1.35.236  # Optional: specify internal IP
  ports:
  - port: 80
    targetPort: 3000
    protocol: TCP
  selector:
    app: grafana
```

**Option B: Helm Values (like your Grafana example)**

```yaml
# values-grafana.yaml
service:
  type: LoadBalancer
  loadBalancerIP: 10.1.35.236
  annotations:
    service.beta.kubernetes.io/azure-load-balancer-internal: "true"
    service.beta.kubernetes.io/azure-pls-create: "true"
    service.beta.kubernetes.io/azure-pls-name: "eos-oss-westus3-observ-grafana-pst-pls"
    service.beta.kubernetes.io/azure-pls-ip-configuration-subnet: "pls-subnet"
    service.beta.kubernetes.io/azure-pls-ip-configuration-ip-address-count: "1"
```

### Step 3: Deploy/Update the Service

```bash
# For direct YAML
kubectl apply -f service.yaml

# For Helm
helm upgrade grafana grafana/grafana \
  --namespace grafana \
  --values values-grafana.yaml
```

### Step 4: Verify PLS Creation

```bash
# Wait a few minutes for Azure to create the PLS
sleep 60

# Check the service status
kubectl get svc grafana -n grafana

# Get the LoadBalancer IP
kubectl get svc grafana -n grafana -o jsonpath='{.status.loadBalancer.ingress[0].ip}'

# Check Azure for the PLS
RESOURCE_GROUP="MC_your-aks-rg_your-aks-cluster_region"  # AKS managed RG
az network private-link-service list \
  --resource-group $RESOURCE_GROUP \
  --output table
```

---

## Method 2: Manual PLS Creation via Azure Portal

Use this method if you want more control or if automatic creation doesn't work.

### Step 1: Create Internal LoadBalancer Service in AKS

```yaml
apiVersion: v1
kind: Service
metadata:
  name: grafana
  namespace: grafana
  annotations:
    service.beta.kubernetes.io/azure-load-balancer-internal: "true"
spec:
  type: LoadBalancer
  loadBalancerIP: 10.1.35.236
  ports:
  - port: 80
    targetPort: 3000
  selector:
    app: grafana
```

Apply it:
```bash
kubectl apply -f service.yaml
```

Wait for the LoadBalancer to be provisioned and note the IP address.

### Step 2: Find the LoadBalancer Resource in Azure

```bash
# Get the AKS managed resource group
AKS_MC_RG=$(az aks show \
  --resource-group your-aks-rg \
  --name your-aks-cluster \
  --query nodeResourceGroup -o tsv)

echo "AKS Managed RG: $AKS_MC_RG"

# Find the LoadBalancer
az network lb list \
  --resource-group $AKS_MC_RG \
  --output table

# Get LoadBalancer details
LB_NAME="kubernetes-internal"  # Usually this name for internal LB
az network lb show \
  --resource-group $AKS_MC_RG \
  --name $LB_NAME
```

### Step 3: Create Private Link Service via Portal

1. **Go to Azure Portal** → Search for "Private Link"
2. Click **"Private link services"** → **"+ Create"**
3. Fill in the basics:
   - **Subscription**: Your subscription
   - **Resource Group**: Your AKS managed RG (MC_...)
   - **Name**: `eos-oss-westus3-observ-grafana-pst-pls`
   - **Region**: Same as your AKS cluster

4. **Outbound settings** tab:
   - **Load balancer**: Select your internal LoadBalancer (kubernetes-internal)
   - **Frontend IP configuration**: Select the frontend IP (usually has the service IP)
   - **Source NAT subnet**: Select your PLS subnet
   - **Enable TCP proxy V2**: Disable (unless your app needs it)
   - **Private IP address**: Let Azure choose automatically

5. **Access security** tab:
   - **Visibility**: 
     - **Restricted by subscription**: Add allowed subscription IDs
     - **OR Role-based**: Anyone with proper permissions
   - **Auto-approval**:
     - Add subscription IDs that should be auto-approved

6. **Tags** tab: Add any tags you need

7. **Review + create** → **Create**

### Step 4: Verify and Get Alias

After creation:
1. Go to the Private Link Service resource
2. Copy the **Alias** - this is what consumers use to connect
3. Format: `<pls-name>.<region>.azure.privatelinkservice`

---

## Method 3: Manual PLS Creation via Azure CLI

### Step 1: Create the Internal LoadBalancer Service (same as Method 2, Step 1)

### Step 2: Get LoadBalancer Information

```bash
# Set variables
RESOURCE_GROUP="your-aks-rg"
AKS_CLUSTER_NAME="your-aks-cluster"

# Get the managed resource group
AKS_MC_RG=$(az aks show \
  --resource-group $RESOURCE_GROUP \
  --name $AKS_CLUSTER_NAME \
  --query nodeResourceGroup -o tsv)

echo "AKS Managed Resource Group: $AKS_MC_RG"

# List LoadBalancers
az network lb list \
  --resource-group $AKS_MC_RG \
  --output table

# Get the internal LoadBalancer name and ID
LB_NAME="kubernetes-internal"
LB_ID=$(az network lb show \
  --resource-group $AKS_MC_RG \
  --name $LB_NAME \
  --query id -o tsv)

echo "LoadBalancer ID: $LB_ID"

# Get the frontend IP configuration name
FRONTEND_IP_CONFIG=$(az network lb show \
  --resource-group $AKS_MC_RG \
  --name $LB_NAME \
  --query "frontendIPConfigurations[?privateIPAddress=='10.1.35.236'].name" -o tsv)

echo "Frontend IP Config: $FRONTEND_IP_CONFIG"
```

### Step 3: Get Subnet Information

```bash
# Get your VNet details
VNET_NAME="your-aks-vnet"
VNET_RG="your-vnet-rg"  # May be different from AKS RG
PLS_SUBNET_NAME="pls-subnet"

# Get subnet ID
PLS_SUBNET_ID=$(az network vnet subnet show \
  --resource-group $VNET_RG \
  --vnet-name $VNET_NAME \
  --name $PLS_SUBNET_NAME \
  --query id -o tsv)

echo "PLS Subnet ID: $PLS_SUBNET_ID"

# Ensure private link service network policies are disabled
az network vnet subnet update \
  --resource-group $VNET_RG \
  --vnet-name $VNET_NAME \
  --name $PLS_SUBNET_NAME \
  --disable-private-link-service-network-policies true
```

### Step 4: Create the Private Link Service

```bash
# Set PLS name
PLS_NAME="eos-oss-westus3-observ-grafana-pst-pls"

# Create Private Link Service
az network private-link-service create \
  --name $PLS_NAME \
  --resource-group $AKS_MC_RG \
  --vnet-name $VNET_NAME \
  --subnet $PLS_SUBNET_NAME \
  --lb-frontend-ip-configs $FRONTEND_IP_CONFIG \
  --load-balancer $LB_NAME \
  --location westus3 \
  --enable-proxy-protocol false

# Optional: Add auto-approval for specific subscriptions
# az network private-link-service update \
#   --name $PLS_NAME \
#   --resource-group $AKS_MC_RG \
#   --auto-approval subscriptions="sub-id-1" "sub-id-2"

# Optional: Add visibility for specific subscriptions
# az network private-link-service update \
#   --name $PLS_NAME \
#   --resource-group $AKS_MC_RG \
#   --visibility subscriptions="sub-id-1" "sub-id-2"
```

### Step 5: Get the PLS Alias

```bash
# Get the alias (used by consumers to connect)
PLS_ALIAS=$(az network private-link-service show \
  --name $PLS_NAME \
  --resource-group $AKS_MC_RG \
  --query alias -o tsv)

echo "Private Link Service Alias: $PLS_ALIAS"
echo "Consumers can use this alias to create Private Endpoints"
```

---

## Method 4: Terraform/IaC Approach

### Terraform Configuration

```hcl
# variables.tf
variable "resource_group_name" {
  description = "AKS managed resource group name"
  type        = string
}

variable "vnet_name" {
  description = "VNet name"
  type        = string
}

variable "pls_subnet_name" {
  description = "Private Link Service subnet name"
  type        = string
  default     = "pls-subnet"
}

variable "pls_name" {
  description = "Private Link Service name"
  type        = string
}

variable "lb_frontend_ip_config_name" {
  description = "LoadBalancer frontend IP configuration name"
  type        = string
}

variable "lb_name" {
  description = "LoadBalancer name"
  type        = string
  default     = "kubernetes-internal"
}

variable "location" {
  description = "Azure region"
  type        = string
}

# main.tf
data "azurerm_lb" "aks_internal_lb" {
  name                = var.lb_name
  resource_group_name = var.resource_group_name
}

data "azurerm_subnet" "pls_subnet" {
  name                 = var.pls_subnet_name
  virtual_network_name = var.vnet_name
  resource_group_name  = var.resource_group_name
}

resource "azurerm_private_link_service" "aks_service_pls" {
  name                = var.pls_name
  location            = var.location
  resource_group_name = var.resource_group_name

  nat_ip_configuration {
    name      = "primary"
    primary   = true
    subnet_id = data.azurerm_subnet.pls_subnet.id
  }

  load_balancer_frontend_ip_configuration_ids = [
    "${data.azurerm_lb.aks_internal_lb.id}/frontendIPConfigurations/${var.lb_frontend_ip_config_name}"
  ]

  enable_proxy_protocol = false

  # Optional: Auto-approval
  # auto_approval_subscription_ids = [
  #   "subscription-id-1",
  #   "subscription-id-2"
  # ]

  # Optional: Visibility
  # visibility_subscription_ids = [
  #   "subscription-id-1",
  #   "subscription-id-2"
  # ]

  tags = {
    Environment = "production"
    ManagedBy   = "Terraform"
  }
}

# outputs.tf
output "private_link_service_id" {
  description = "Private Link Service resource ID"
  value       = azurerm_private_link_service.aks_service_pls.id
}

output "private_link_service_alias" {
  description = "Private Link Service alias for consumers"
  value       = azurerm_private_link_service.aks_service_pls.alias
}
```

Apply with:
```bash
terraform init
terraform plan
terraform apply
```

---

## Verification and Testing

### 1. Verify PLS is Created

```bash
# Azure CLI
az network private-link-service list \
  --resource-group $AKS_MC_RG \
  --output table

# Get details
az network private-link-service show \
  --name $PLS_NAME \
  --resource-group $AKS_MC_RG \
  --output json
```

### 2. Check Kubernetes Service

```bash
# Verify service has LoadBalancer IP
kubectl get svc -n grafana

# Check service annotations
kubectl get svc grafana -n grafana -o yaml | grep -A 10 annotations
```

### 3. Create Private Endpoint (Consumer Side)

On the consuming side (could be another subscription/VNet):

```bash
# Consumer variables
CONSUMER_RG="consumer-rg"
CONSUMER_VNET="consumer-vnet"
CONSUMER_SUBNET="pe-subnet"
PE_NAME="grafana-pe"
PLS_ALIAS="<from-provider-pls-alias>"

# Create Private Endpoint
az network private-endpoint create \
  --name $PE_NAME \
  --resource-group $CONSUMER_RG \
  --vnet-name $CONSUMER_VNET \
  --subnet $CONSUMER_SUBNET \
  --private-connection-resource-id "/subscriptions/.../privateLinkServices/$PLS_NAME" \
  --connection-name "grafana-connection" \
  --location westus3 \
  --manual-request false  # Set to true if not auto-approved
```

Or use the alias:
```bash
az network private-endpoint create \
  --name $PE_NAME \
  --resource-group $CONSUMER_RG \
  --vnet-name $CONSUMER_VNET \
  --subnet $CONSUMER_SUBNET \
  --connection-name "grafana-connection" \
  --private-connection-resource-alias $PLS_ALIAS \
  --location westus3
```

### 4. Test Connectivity

```bash
# From consumer side, get Private Endpoint IP
PE_IP=$(az network private-endpoint show \
  --name $PE_NAME \
  --resource-group $CONSUMER_RG \
  --query 'customDnsConfigs[0].ipAddresses[0]' -o tsv)

echo "Private Endpoint IP: $PE_IP"

# Test connectivity
curl -I http://$PE_IP
```

### 5. Setup Private DNS Zone (Optional but Recommended)

For friendly DNS names like `grafana.privatelink.westus3.azmk8s.io` or custom like `*.azprv.3pc.att.com`:

```bash
# Create Private DNS Zone
az network private-dns zone create \
  --resource-group $CONSUMER_RG \
  --name "azprv.3pc.att.com"

# Link to VNet
az network private-dns link vnet create \
  --resource-group $CONSUMER_RG \
  --zone-name "azprv.3pc.att.com" \
  --name "consumer-vnet-link" \
  --virtual-network $CONSUMER_VNET \
  --registration-enabled false

# Create A record pointing to Private Endpoint
az network private-dns record-set a add-record \
  --resource-group $CONSUMER_RG \
  --zone-name "azprv.3pc.att.com" \
  --record-set-name "eos-oss-westus3-observ-grafana-pst-pls" \
  --ipv4-address $PE_IP
```

Now test with DNS:
```bash
nslookup eos-oss-westus3-observ-grafana-pst-pls.azprv.3pc.att.com
curl -I http://eos-oss-westus3-observ-grafana-pst-pls.azprv.3pc.att.com
```

---

## Troubleshooting

### Issue 1: PLS Not Created Automatically

**Symptoms**: Service gets LoadBalancer IP but no PLS appears in Azure

**Solutions**:
1. Check AKS version supports PLS annotations (1.22+)
2. Verify subnet has `disable-private-link-service-network-policies` set to `true`
3. Check annotations are correctly formatted in YAML
4. Review AKS cloud-controller-manager logs:
   ```bash
   kubectl logs -n kube-system -l component=cloud-controller-manager
   ```

### Issue 2: LoadBalancer Stuck in Pending

**Symptoms**: Service shows `<pending>` for EXTERNAL-IP

**Solutions**:
```bash
# Check service events
kubectl describe svc grafana -n grafana

# Check cloud-provider logs
kubectl logs -n kube-system -l component=cloud-controller-manager

# Common causes:
# - Subnet exhaustion
# - Invalid loadBalancerIP
# - Network policies blocking
```

### Issue 3: Private Endpoint Connection Fails

**Symptoms**: Can't connect through Private Endpoint

**Solutions**:
1. Check Private Endpoint connection status:
   ```bash
   az network private-link-service show \
     --name $PLS_NAME \
     --resource-group $AKS_MC_RG \
     --query 'privateEndpointConnections[].{Name:name, Status:privateLinkServiceConnectionState.status}'
   ```

2. If status is "Pending", approve it:
   ```bash
   PE_CONNECTION_NAME="<connection-name>"
   az network private-link-service connection update \
     --name $PE_CONNECTION_NAME \
     --resource-group $AKS_MC_RG \
     --service-name $PLS_NAME \
     --connection-status Approved \
     --description "Approved"
   ```

3. Check NSG rules on both subnets
4. Verify routing tables

### Issue 4: Can't Find LoadBalancer Frontend IP Config

**Symptoms**: Error when trying to attach PLS to LoadBalancer

**Solutions**:
```bash
# List all frontend IPs
az network lb frontend-ip list \
  --lb-name $LB_NAME \
  --resource-group $AKS_MC_RG \
  --output table

# Check specific IP
az network lb frontend-ip list \
  --lb-name $LB_NAME \
  --resource-group $AKS_MC_RG \
  --query "[?privateIPAddress=='10.1.35.236']"
```

### Issue 5: Annotations Not Applied After Helm Upgrade

**Symptoms**: Service doesn't update with new annotations

**Solutions**:
```bash
# Force helm upgrade
helm upgrade grafana grafana/grafana \
  --namespace grafana \
  --values values-grafana.yaml \
  --force

# Or delete and recreate service
kubectl delete svc grafana -n grafana
helm upgrade grafana grafana/grafana \
  --namespace grafana \
  --values values-grafana.yaml
```

---

## Best Practices

### 1. Subnet Planning
- Use a dedicated subnet for PLS (don't mix with node pools)
- Size appropriately (at least /28, but /27 or /26 is better)
- Ensure `disable-private-link-service-network-policies` is enabled

### 2. Naming Conventions
- Use descriptive PLS names: `<environment>-<service>-<region>-pls`
- Keep names DNS-friendly (alphanumeric and hyphens only)

### 3. Security
- Use auto-approval only for trusted subscriptions
- Limit visibility to required subscriptions
- Implement NSG rules on PLS subnet
- Monitor Private Endpoint connections

### 4. High Availability
- PLS inherits HA from the LoadBalancer
- Consider multiple PLS for different services
- Use availability zones if available

### 5. Monitoring
- Monitor LoadBalancer metrics
- Track Private Endpoint connection requests
- Set up alerts for PLS connectivity issues

---

## Quick Reference - All PLS Annotations

```yaml
metadata:
  annotations:
    # LoadBalancer Configuration
    service.beta.kubernetes.io/azure-load-balancer-internal: "true"
    service.beta.kubernetes.io/azure-load-balancer-internal-subnet: "aks-subnet"
    
    # Private Link Service Creation
    service.beta.kubernetes.io/azure-pls-create: "true"
    service.beta.kubernetes.io/azure-pls-name: "my-service-pls"
    
    # PLS IP Configuration
    service.beta.kubernetes.io/azure-pls-ip-configuration-subnet: "pls-subnet"
    service.beta.kubernetes.io/azure-pls-ip-configuration-ip-address-count: "1"
    
    # PLS Access Control
    service.beta.kubernetes.io/azure-pls-auto-approval: "sub-id-1,sub-id-2"
    service.beta.kubernetes.io/azure-pls-visibility: "sub-id-1,sub-id-2,*"
    
    # PLS Optional Features
    service.beta.kubernetes.io/azure-pls-proxy-protocol: "false"
    service.beta.kubernetes.io/azure-pls-fqdns: "fqdn1.com,fqdn2.com"
```

---

## Additional Resources

- [Azure Private Link Service Documentation](https://learn.microsoft.com/en-us/azure/private-link/private-link-service-overview)
- [AKS Private Link Service Integration](https://learn.microsoft.com/en-us/azure/aks/internal-lb#create-a-private-link-service)
- [Azure Cloud Provider for Kubernetes](https://cloud-provider-azure.sigs.k8s.io/)
- [Private Link Pricing](https://azure.microsoft.com/en-us/pricing/details/private-link/)

---

## Private Link Service - Deep Dive: What You CAN and CANNOT Do

### Overview

Azure Private Link Service (PLS) is a powerful networking feature that enables you to securely expose your services to consumers across different VNets, subscriptions, or even tenants, without requiring VNet peering, public IPs, or complex routing.

---

### ✅ What You CAN Do with Private Link Service

#### 1. **Cross-VNet Connectivity Without Peering**

```
Provider VNet              Consumer VNet (Different VNet/Region/Subscription)
├─ 10.1.0.0/16            ├─ 192.168.0.0/16
│  └─ PLS                 │  └─ Private Endpoint
│                         │
└─────── NO PEERING ──────┘
         ✓ Direct private connection via Azure backbone
```

**Benefits:**
- ✅ No VNet peering required
- ✅ Works across Azure regions
- ✅ Works across Azure subscriptions
- ✅ Works across Azure tenants (with proper permissions)
- ✅ Overlapping IP spaces are OK!

**Use Cases:**
- Multi-tenant SaaS applications
- Cross-organization secure connectivity
- Shared services across business units
- Partner/vendor integrations

---

#### 2. **Support for Overlapping IP Address Spaces**

```
Scenario: Multiple consumers with same IP ranges

Provider VNet: 10.0.0.0/8
└─ PLS: my-service-pls

Consumer 1 VNet: 10.0.0.0/8  ← Same!
└─ PE: 10.50.1.10 → PLS

Consumer 2 VNet: 10.0.0.0/8  ← Same!
└─ PE: 10.75.2.20 → PLS

Result: ✅ Both work! Each PE has local IP in its own VNet
```

**Why it works:**
- Private Endpoints use **local IPs** in consumer VNets
- No direct routing between provider and consumer
- Traffic proxied through Azure backbone
- NAT happens transparently

**Benefits:**
- ✅ Simplifies multi-tenant architectures
- ✅ No IP address coordination needed
- ✅ Each consumer uses their own IP space
- ✅ Provider doesn't see consumer IPs

---

#### 3. **Control Access with Fine-Grained Permissions**

**A. Auto-Approval by Subscription**
```yaml
annotations:
  service.beta.kubernetes.io/azure-pls-auto-approval: "sub-id-1,sub-id-2"
```

**B. Visibility Control**
```yaml
annotations:
  service.beta.kubernetes.io/azure-pls-visibility: "sub-id-1,sub-id-2,*"
```

**C. Manual Approval Workflow**
```bash
# Consumer requests connection
az network private-endpoint create --manual-request true

# Provider reviews and approves
az network private-link-service connection update \
  --connection-status Approved \
  --description "Approved for partner XYZ"
```

**Access Control Matrix:**

| Setting | Auto-Approval | Visibility | Manual Approval | Use Case |
|---------|--------------|------------|-----------------|----------|
| Default | ❌ | All Azure | ✅ Required | Open marketplace |
| Subscription List | ✅ Trusted subs | Listed subs | ❌ Not needed | Partner ecosystem |
| RBAC only | ❌ | RBAC users | ✅ Required | Internal corporate |
| Wildcard (*) | ❌ | Everyone | ✅ Required | Public service |

---

#### 4. **Multi-Region Support**

```
Provider (West US 3)              Consumer (East US)
├─ PLS: my-app-pls               ├─ Private Endpoint
│  └─ LoadBalancer               │  └─ Connects cross-region
│                                │
└────── Azure Global Network ─────┘
         ✓ Low latency, high bandwidth
```

**Capabilities:**
- ✅ PLS in one region, consumers in any region
- ✅ Automatic cross-region routing
- ✅ Azure backbone network (fast & secure)
- ✅ No additional configuration needed

**Considerations:**
- 💡 Cross-region data transfer costs apply
- 💡 Latency depends on geographic distance
- 💡 Consider availability zones for HA

---

#### 5. **Support Multiple Consumers (1-to-Many)**

```
              ┌─ Consumer 1 (PE-1)
              │
Provider PLS ─┼─ Consumer 2 (PE-2)
              │
              ├─ Consumer 3 (PE-3)
              │
              └─ Consumer N (PE-N)
```

**Limits:**
- ✅ Up to **1,000 Private Endpoint connections** per PLS
- ✅ Each connection tracked independently
- ✅ Individual approval/rejection per connection
- ✅ Each consumer gets their own Private Endpoint

**Use Cases:**
- Multi-tenant SaaS platforms
- Shared analytics services
- Centralized logging/monitoring
- Enterprise service catalog

---

#### 6. **Integration with Standard Load Balancer**

**Supported Load Balancer Types:**
```
✅ Standard Load Balancer (Internal)
✅ Standard Load Balancer (Public)
❌ Basic Load Balancer
```

**Configuration:**
```yaml
# Internal Load Balancer (most common)
annotations:
  service.beta.kubernetes.io/azure-load-balancer-internal: "true"
  service.beta.kubernetes.io/azure-pls-create: "true"

# Public Load Balancer (also works!)
annotations:
  service.beta.kubernetes.io/azure-pls-create: "true"
```

**Benefits:**
- ✅ Use existing LoadBalancer configurations
- ✅ Multiple frontend IPs supported
- ✅ HA and scaling from LoadBalancer
- ✅ Health probes work automatically

---

#### 7. **Custom DNS Integration**

**A. Azure Private DNS Zone**
```bash
# Create private DNS zone
az network private-dns zone create \
  --resource-group $RG \
  --name "privatelink.myservice.com"

# Link to consumer VNet
az network private-dns link vnet create \
  --zone-name "privatelink.myservice.com" \
  --virtual-network $CONSUMER_VNET

# Auto-creates A record for Private Endpoint
Result: myapp.privatelink.myservice.com → 10.x.x.x
```

**B. Custom DNS (like AT&T's .azprv.3pc.att.com)**
```bash
# Enterprise DNS management
Consumer queries: grafana.azprv.3pc.att.com
                  └─ Resolves to Private Endpoint IP
```

**Capabilities:**
- ✅ Automatic DNS integration with Azure Private DNS
- ✅ Custom DNS names supported
- ✅ Multiple DNS zones per PLS
- ✅ Split-horizon DNS (internal vs external)

---

#### 8. **Traffic Transparency with Proxy Protocol v2**

```yaml
annotations:
  service.beta.kubernetes.io/azure-pls-proxy-protocol: "true"
```

**What it provides:**
- ✅ Original client IP visible to backend
- ✅ Client port information preserved
- ✅ Useful for logging/auditing/security

**Requirements:**
- Application must support PROXY protocol v2
- Common in: NGINX, HAProxy, Envoy, etc.
- Not supported by all applications

**Without Proxy Protocol:**
```
Backend sees: Azure NAT IP (e.g., 168.63.129.16)
```

**With Proxy Protocol:**
```
Backend sees: Original consumer Private Endpoint IP
```

---

#### 9. **Integration with Azure Kubernetes Service (AKS)**

**Automatic Creation via Annotations:**
```yaml
apiVersion: v1
kind: Service
metadata:
  annotations:
    service.beta.kubernetes.io/azure-pls-create: "true"
spec:
  type: LoadBalancer
```

**Benefits:**
- ✅ Declarative configuration
- ✅ GitOps-friendly
- ✅ Automatic lifecycle management
- ✅ No manual Azure Portal work needed

**Supported AKS Versions:**
- ✅ AKS 1.22+
- ✅ Azure CNI or Kubenet
- ✅ Works with Calico, Azure Network Policy

---

#### 10. **Monitoring and Diagnostics**

**Available Metrics:**
```bash
# Connection count
az monitor metrics list \
  --resource $PLS_ID \
  --metric "ConnectionCount"

# Bytes transferred
az monitor metrics list \
  --resource $PLS_ID \
  --metric "BytesReceived,BytesSent"
```

**Diagnostic Logs:**
- ✅ Connection requests (approved/denied)
- ✅ Bytes in/out per connection
- ✅ Connection duration
- ✅ Error rates

**Integration:**
- ✅ Azure Monitor
- ✅ Log Analytics
- ✅ Azure Sentinel
- ✅ Third-party SIEM

---

### ❌ What You CANNOT Do with Private Link Service

#### 1. **Cannot Use with Basic Load Balancer**

```
❌ Basic Load Balancer → PLS
✅ Standard Load Balancer → PLS
```

**Reason:**
- Basic LB doesn't support frontend IP configuration required for PLS
- Must upgrade to Standard Load Balancer

**Migration Path:**
```bash
# Cannot directly upgrade
# Must create new Standard LB and migrate
```

---

#### 2. **Cannot Use with Public IP Addresses Directly**

```
❌ Public IP → PLS (without Load Balancer)
✅ Public IP → Standard LB → PLS
```

**Clarification:**
- PLS must attach to a **Load Balancer frontend IP**
- Cannot attach directly to a VM's public IP
- Cannot attach to Application Gateway public IP

**Workaround:**
```
VM → Standard Load Balancer → PLS
         ↑
    (Frontend IP can be public or private)
```

---

#### 3. **Cannot Route Between Provider and Consumer VNets**

```
Provider VNet: 10.1.0.0/16        Consumer VNet: 192.168.0.0/16
├─ Service A: 10.1.1.10           ├─ PE → PLS → Service A ✅
├─ Service B: 10.1.2.20           ├─ Direct access to 10.1.2.20 ❌
└─ PLS                            └─ No routing to provider VNet
```

**Limitations:**
- ❌ No full network connectivity
- ❌ Only services exposed via PLS are accessible
- ❌ Cannot ping/traceroute to provider VNet
- ❌ No broadcast/multicast support

**Why:**
- Private Link is **service-level**, not network-level
- No routing tables exchanged
- No BGP peering
- Traffic only flows to PLS-exposed services

**When you need full connectivity:**
```
Use: VNet Peering, VPN Gateway, or ExpressRoute
(But remember: these don't support overlapping IPs!)
```

---

#### 4. **Cannot Support Protocols Other Than TCP**

```
✅ TCP (all ports)
❌ UDP
❌ ICMP (ping)
❌ GRE
❌ ESP (IPsec)
```

**Impact:**
- ❌ No UDP-based services (DNS, QUIC, VoIP)
- ❌ Cannot ping Private Endpoint
- ❌ No IPsec VPN over Private Link
- ❌ No multicast/broadcast

**Workarounds:**
- Use TCP-based alternatives (DNS over TCP/TLS, HTTP/3 over TCP)
- For UDP: Use VNet Peering or VPN Gateway instead

---

#### 5. **Cannot Exceed Scaling Limits**

**Hard Limits:**

| Resource | Limit | Scope |
|----------|-------|-------|
| Private Endpoints per PLS | 1,000 | Per PLS |
| Private Link Services per subscription | 800 | Per subscription |
| Private Link Services per region | No specific limit | Limited by other resources |
| Connections per Private Endpoint | 1 | Per PE |
| Frontend IPs per PLS | 8 | Per PLS |

**Soft Limits (can request increase):**
- Private Endpoints per subscription: Default 1,000
- Private Endpoints per VNet: Default 1,000

**Impact:**
```
Scenario: 2,000 consumers need access

❌ Cannot: 2,000 PEs → 1 PLS (exceeds limit)

✅ Can: 
   - 1,000 PEs → PLS-1
   - 1,000 PEs → PLS-2 (both pointing to same LB)
```

---

#### 6. **Cannot Modify After Creation (Limited Changes)**

**Cannot Change:**
- ❌ Load Balancer association (must delete/recreate)
- ❌ Subnet (must delete/recreate)
- ❌ Location/region (must delete/recreate)

**Can Change:**
- ✅ Auto-approval subscriptions
- ✅ Visibility settings
- ✅ Tags
- ✅ Enable/disable proxy protocol

**Workaround for major changes:**
```bash
# Must delete and recreate
1. Delete PLS
2. Create new PLS with new configuration
3. Consumers must recreate Private Endpoints
4. Update DNS records
```

---

#### 7. **Cannot Use with IPv6 (Currently)**

```
✅ IPv4 fully supported
❌ IPv6 not supported (as of 2025)
❌ Dual-stack not supported
```

**Impact:**
- Must use IPv4 addresses
- No IPv6-only networks
- Dual-stack VNets must use IPv4 for PLS

---

#### 8. **Cannot Guarantee Specific Performance SLA**

**Performance Characteristics:**
- ✅ Leverages Azure backbone network (high performance)
- ⚠️ No specific bandwidth/latency SLA for Private Link itself
- ⚠️ Performance depends on underlying services (VM, LB, etc.)

**What impacts performance:**
```
1. Load Balancer SKU and configuration
2. Backend service capacity
3. Network distance (cross-region)
4. VM/container resources
5. Concurrent connections
```

**Best Practices:**
- Use Standard Load Balancer (better performance)
- Deploy in same region when possible
- Monitor and scale backend services
- Use availability zones

---

#### 9. **Cannot Share Private Endpoints Across Connections**

```
❌ Cannot:
Consumer VNet
├─ VM-A ─┐
├─ VM-B ─┼─ Shared PE → PLS
└─ VM-C ─┘

✅ Can:
Consumer VNet
├─ PE (single shared resource) → PLS
│   ↑
│   └─ All VMs in VNet can use this PE
```

**Clarification:**
- ✅ One PE per consumer VNet/subnet (all VMs share it)
- ❌ Cannot reuse same PE from different VNets
- ❌ Each consumer VNet needs its own PE

---

#### 10. **Cannot Bypass Provider's Access Controls**

```
Provider sets:
- Auto-approval: subscription-123
- Visibility: subscription-123, subscription-456

Consumer from subscription-789:
❌ Cannot see the PLS
❌ Cannot create Private Endpoint
❌ Cannot connect even with PLS alias
```

**Access Control Enforcement:**
- ✅ Visibility controls who can **discover** PLS
- ✅ Auto-approval controls who can **connect automatically**
- ✅ Manual approval required for all others
- ❌ No way to bypass these controls

**Security Note:**
- Provider has full control over who connects
- Connections can be rejected at any time
- Connections can be removed after establishment

---

#### 11. **Cannot Do Source NAT Control**

**Fixed Behavior:**
```
Consumer sends traffic from: 10.50.1.10 (PE IP)
                            ↓
                      Azure NAT
                            ↓
Provider receives from: Azure NAT IP (e.g., 168.63.129.16)
```

**Limitations:**
- ❌ Cannot preserve consumer's original IP (without PROXY protocol)
- ❌ Cannot control which IP provider sees
- ❌ Cannot disable NAT

**Workaround:**
```yaml
# Enable PROXY protocol v2
service.beta.kubernetes.io/azure-pls-proxy-protocol: "true"

Requirements:
- Application must support PROXY protocol
- Parses protocol header to get original IP
```

---

#### 12. **Cannot Use with Network Virtual Appliances (NVA) Directly**

```
❌ Cannot: VM (NVA) → PLS
❌ Cannot: Firewall VM → PLS

✅ Can: VM → Standard LB → PLS
```

**Reason:**
- PLS requires Standard Load Balancer frontend
- NVAs don't have LoadBalancer integration
- Must place NVA behind a Standard LB

**Architecture:**
```
Traffic flow:
Consumer → PE → PLS → Standard LB → NVA (as backend) → App
```

---

#### 13. **Cannot Expose Multiple Services on Same Port from Single PLS**

```
❌ Cannot:
Single PLS:
├─ Service A (port 443)
└─ Service B (port 443)  ← Conflict!

✅ Can:
Single PLS:
├─ Service A (port 443)
└─ Service B (port 8443)  ← Different port

OR

PLS-1 → Service A (port 443)
PLS-2 → Service B (port 443)  ← Separate PLS
```

**Limitation:**
- Each PLS frontend IP can only listen on each port once
- Must use different ports or different PLS instances

---

#### 14. **Cannot Do Application-Layer Routing/Inspection**

**PLS is Layer 4 (TCP) only:**
```
❌ Cannot: HTTP host-based routing (layer 7)
❌ Cannot: TLS SNI routing (layer 7)
❌ Cannot: Deep packet inspection
❌ Cannot: WAF/DDoS at PLS level
```

**Workaround:**
```
Consumer → PE → PLS → Application Gateway (L7) → Apps
                       └─ Can do L7 routing here
```

**For your use case:**
- Use Application Gateway or API Management behind PLS
- Do L7 routing/security at application layer
- PLS just handles secure connectivity

---

### Comparison: Private Link vs Other Azure Networking Options

| Feature | Private Link | VNet Peering | VPN Gateway | ExpressRoute |
|---------|-------------|--------------|-------------|--------------|
| Overlapping IPs | ✅ Yes | ❌ No | ❌ No | ❌ No |
| Cross-region | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| Cross-tenant | ✅ Yes | ✅ Yes (complex) | ❌ No | ✅ Yes |
| Full network access | ❌ Service-level | ✅ Full | ✅ Full | ✅ Full |
| UDP support | ❌ No | ✅ Yes | ✅ Yes | ✅ Yes |
| Bandwidth | High | Very High | Limited | Very High |
| Latency | Low | Very Low | Medium | Very Low |
| Setup complexity | Low | Very Low | Medium | High |
| Cost | Per hour + GB | Per GB | Per hour + GB | High (circuit) |
| Scalability | 1000 PEs/PLS | High | Limited | High |
| Security | Excellent | Good | Excellent | Excellent |

---

### When to Use Private Link Service

**✅ Use Private Link Service When:**

1. **Multi-tenant scenarios**
   - SaaS applications
   - Shared services across organizations
   - Partner integrations

2. **Overlapping IP addresses**
   - Cannot coordinate IP spaces
   - Multiple isolated networks
   - Legacy systems with fixed IPs

3. **Service-level exposure**
   - Only specific services need exposure
   - Want granular access control
   - Don't need full network connectivity

4. **Cross-tenant/subscription access**
   - Different Azure subscriptions
   - Different Azure AD tenants
   - External partners/customers

5. **Simplified connectivity**
   - Want to avoid VNet peering complexity
   - Don't want to manage route tables
   - Need easy consumer onboarding

**❌ Don't Use Private Link Service When:**

1. **Need full network connectivity**
   - Multiple services without load balancer
   - Need to access all resources in VNet
   - Require network-level protocols

2. **Need UDP support**
   - DNS services (use Private DNS instead)
   - VoIP/media streaming
   - Gaming applications

3. **Need Layer 7 features**
   - HTTP/HTTPS routing by path
   - TLS termination at edge
   - WAF/DDoS protection
   - (Use Application Gateway or API Management instead)

4. **Can coordinate IP spaces**
   - Same organization
   - Can plan network addressing
   - VNet Peering is simpler

5. **Need lowest possible latency**
   - Ultra-low latency requirements
   - Consider VNet Peering or ExpressRoute

---

### Cost Considerations

**Private Link Service Pricing (as of 2025):**

```
1. Private Link Service: ~$0.01/hour per PLS
2. Data Processed: ~$0.01/GB inbound
3. Private Endpoint (consumer): ~$0.01/hour per PE

Example Monthly Cost:
- 1 PLS (24/7): $0.01 * 24 * 30 = $7.20
- 100 PEs (consumers): $0.01 * 24 * 30 * 100 = $720
- Data transfer (1TB): $0.01 * 1000 = $10
Total: ~$737/month
```

**Cost Optimization:**
- Consolidate multiple services behind one LoadBalancer
- Use same PLS for multiple frontend IPs (up to 8)
- Monitor and remove unused Private Endpoints
- Consider regional data transfer costs

---

## Summary

**For most use cases, use Method 1 (Kubernetes Annotations)** - it's the simplest and most maintainable approach. The annotations handle everything automatically, and you can manage it all through your Helm charts or Kubernetes manifests.

Use manual methods (2 or 3) only when:
- You need more granular control
- Automatic creation isn't working
- You're working with existing LoadBalancers
- Your organization requires manual approval workflows

For production environments, consider Method 4 (Terraform) for complete infrastructure-as-code management.

### Key Takeaways:

**Private Link Service is excellent for:**
- ✅ Multi-tenant service exposure
- ✅ Cross-subscription/tenant connectivity
- ✅ Overlapping IP address spaces
- ✅ Granular access control
- ✅ Simplified network management

**But has limitations:**
- ❌ TCP only (no UDP)
- ❌ Service-level, not network-level
- ❌ Requires Standard Load Balancer
- ❌ Some configuration cannot be changed after creation

**For your Grafana/AT&T scenario:**
Your use case is **perfect for Private Link Service** because:
- Need to expose Grafana across multiple VNets/subscriptions
- Want secure connectivity without VNet peering
- AT&T's multi-tenant environment with potentially overlapping IPs
- Service-level exposure is sufficient (just need Grafana access)
- TCP-based service (HTTP/HTTPS)


