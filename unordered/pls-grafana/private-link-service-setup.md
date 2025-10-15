# Azure Private Link Service Setup Guide

This guide provides manual Azure CLI and kubectl commands to set up Azure Private Link Service for your existing AKS infrastructure.

## Prerequisites

- Azure CLI installed and authenticated
- kubectl configured with AKS cluster access
- Appropriate permissions to create Azure resources

## Current Environment

- **Subscription**: DAP_Dev (cda76fc5-a3ee-4c98-b4ba-055125b3de93)
- **AKS Network Plugin**: Azure CNI
- **Load Balancer**: Standard SKU

---

## Step 1: Set Environment Variables

```bash
# Set your variables
export SUBSCRIPTION_ID="cda76fc5-a3ee-4c98-b4ba-055125b3de93"
export RESOURCE_GROUP="<your-aks-resource-group>"
export AKS_CLUSTER_NAME="<your-aks-cluster-name>"
export LOCATION="<your-location>"  # e.g., westus2

# Get the AKS node resource group (MC_* resource group)
export AKS_NODE_RG=$(az aks show \
  --resource-group $RESOURCE_GROUP \
  --name $AKS_CLUSTER_NAME \
  --query nodeResourceGroup -o tsv)

echo "AKS Node Resource Group: $AKS_NODE_RG"

# Get AKS VNet details
export AKS_VNET_NAME=$(az network vnet list \
  --resource-group $AKS_NODE_RG \
  --query "[0].name" -o tsv)

export AKS_VNET_ID=$(az network vnet show \
  --resource-group $AKS_NODE_RG \
  --name $AKS_VNET_NAME \
  --query id -o tsv)

echo "AKS VNet: $AKS_VNET_NAME"
```

---

## Step 2: Create Kubernetes Service with Internal Load Balancer

Create a Kubernetes service manifest that will provision an internal Azure Load Balancer:

```bash
# Create service manifest
cat <<EOF > internal-lb-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: my-internal-service
  namespace: default
  annotations:
    # Use internal load balancer
    service.beta.kubernetes.io/azure-load-balancer-internal: "true"
    
    # Specify subnet for the load balancer (optional)
    # service.beta.kubernetes.io/azure-load-balancer-internal-subnet: "aks-subnet"
    
    # Disable Private Link Service network policies
    service.beta.kubernetes.io/azure-pls-create: "true"
    
    # Specify IP address for load balancer (optional)
    # service.beta.kubernetes.io/azure-load-balancer-ipv4: "10.240.0.100"
    
    # Resource group for load balancer (uses node resource group by default)
    # service.beta.kubernetes.io/azure-load-balancer-resource-group: "$AKS_NODE_RG"
spec:
  type: LoadBalancer
  selector:
    app: my-app  # Change to match your application labels
  ports:
    - protocol: TCP
      port: 443
      targetPort: 8080
      name: https
    - protocol: TCP
      port: 80
      targetPort: 8080
      name: http
EOF

# Apply the service
kubectl apply -f internal-lb-service.yaml

# Wait for the service to get an IP address
kubectl get service my-internal-service --watch

# Get the service details
kubectl describe service my-internal-service
```

---

## Step 3: Get Load Balancer Details

```bash
# Wait a few moments for Azure to create the load balancer
sleep 30

# List load balancers in the node resource group
az network lb list \
  --resource-group $AKS_NODE_RG \
  --query "[].{Name:name, ResourceGroup:resourceGroup}" -o table

# Get the internal load balancer name (usually kubernetes-internal)
export INTERNAL_LB_NAME=$(az network lb list \
  --resource-group $AKS_NODE_RG \
  --query "[?contains(name, 'kubernetes-internal') || contains(name, 'internal')].name" -o tsv | head -1)

# If not found, list all LBs and select manually
if [ -z "$INTERNAL_LB_NAME" ]; then
  echo "Internal LB not found automatically. Available load balancers:"
  az network lb list --resource-group $AKS_NODE_RG --query "[].name" -o tsv
  echo "Please set INTERNAL_LB_NAME manually:"
  echo 'export INTERNAL_LB_NAME="<your-lb-name>"'
else
  echo "Internal Load Balancer: $INTERNAL_LB_NAME"
fi

# Get the frontend IP configuration ID
export LB_FRONTEND_IP_CONFIG_ID=$(az network lb show \
  --resource-group $AKS_NODE_RG \
  --name $INTERNAL_LB_NAME \
  --query "frontendIpConfigurations[0].id" -o tsv)

echo "Frontend IP Config ID: $LB_FRONTEND_IP_CONFIG_ID"

# Get the frontend IP address
export LB_FRONTEND_IP=$(az network lb show \
  --resource-group $AKS_NODE_RG \
  --name $INTERNAL_LB_NAME \
  --query "frontendIpConfigurations[0].privateIPAddress" -o tsv)

echo "Frontend IP Address: $LB_FRONTEND_IP"
```

---

## Step 4: Create Subnet for Private Link Service

Private Link Service requires a dedicated subnet with `privateLinkServiceNetworkPolicies` disabled.

```bash
# Define subnet variables
export PLS_SUBNET_NAME="pls-subnet"
export PLS_SUBNET_PREFIX="10.240.2.0/24"  # Adjust to your VNet address space

# Create the subnet
az network vnet subnet create \
  --resource-group $AKS_NODE_RG \
  --vnet-name $AKS_VNET_NAME \
  --name $PLS_SUBNET_NAME \
  --address-prefixes $PLS_SUBNET_PREFIX \
  --disable-private-link-service-network-policies true

# Get subnet ID
export PLS_SUBNET_ID=$(az network vnet subnet show \
  --resource-group $AKS_NODE_RG \
  --vnet-name $AKS_VNET_NAME \
  --name $PLS_SUBNET_NAME \
  --query id -o tsv)

echo "PLS Subnet ID: $PLS_SUBNET_ID"
```

**Note**: If you need to update an existing subnet instead:

```bash
az network vnet subnet update \
  --resource-group $AKS_NODE_RG \
  --vnet-name $AKS_VNET_NAME \
  --name $PLS_SUBNET_NAME \
  --disable-private-link-service-network-policies true
```

---

## Step 5: Create Private Link Service

```bash
export PLS_NAME="aks-private-link-service"

# Create the Private Link Service
az network private-link-service create \
  --resource-group $RESOURCE_GROUP \
  --name $PLS_NAME \
  --vnet-name $AKS_VNET_NAME \
  --subnet $PLS_SUBNET_NAME \
  --lb-frontend-ip-configs $LB_FRONTEND_IP_CONFIG_ID \
  --location $LOCATION \
  --enable-proxy-protocol false \
  --tags environment=production managed-by=manual

# Get Private Link Service details
az network private-link-service show \
  --resource-group $RESOURCE_GROUP \
  --name $PLS_NAME \
  --query "{Name:name, Alias:alias, ProvisioningState:provisioningState}" -o table

# Get the Private Link Service alias (needed for creating Private Endpoints)
export PLS_ALIAS=$(az network private-link-service show \
  --resource-group $RESOURCE_GROUP \
  --name $PLS_NAME \
  --query alias -o tsv)

echo "Private Link Service Alias: $PLS_ALIAS"
```

---

## Step 6: Configure Auto-Approval and Visibility (Optional)

```bash
# Auto-approve connections from specific subscriptions
az network private-link-service update \
  --resource-group $RESOURCE_GROUP \
  --name $PLS_NAME \
  --auto-approval subscriptions="cda76fc5-a3ee-4c98-b4ba-055125b3de93"

# Set visibility to specific subscriptions
az network private-link-service update \
  --resource-group $RESOURCE_GROUP \
  --name $PLS_NAME \
  --visibility subscriptions="cda76fc5-a3ee-4c98-b4ba-055125b3de93"
```

---

## Step 7: Create Private Endpoint (Consumer Side)

On the consumer side (could be another VNet or subscription):

```bash
# Consumer variables
export CONSUMER_RG="<consumer-resource-group>"
export CONSUMER_VNET_NAME="<consumer-vnet-name>"
export CONSUMER_SUBNET_NAME="<consumer-subnet-name>"
export PRIVATE_ENDPOINT_NAME="aks-service-private-endpoint"

# Disable private endpoint network policies on consumer subnet
az network vnet subnet update \
  --resource-group $CONSUMER_RG \
  --vnet-name $CONSUMER_VNET_NAME \
  --name $CONSUMER_SUBNET_NAME \
  --disable-private-endpoint-network-policies true

# Create Private Endpoint
az network private-endpoint create \
  --resource-group $CONSUMER_RG \
  --name $PRIVATE_ENDPOINT_NAME \
  --vnet-name $CONSUMER_VNET_NAME \
  --subnet $CONSUMER_SUBNET_NAME \
  --private-connection-resource-id $(az network private-link-service show \
    --resource-group $RESOURCE_GROUP \
    --name $PLS_NAME \
    --query id -o tsv) \
  --connection-name "aks-service-connection" \
  --location $LOCATION

# Get Private Endpoint IP
az network private-endpoint show \
  --resource-group $CONSUMER_RG \
  --name $PRIVATE_ENDPOINT_NAME \
  --query "customDnsConfigs[0].ipAddresses[0]" -o tsv
```

---

## Step 8: Approve Private Endpoint Connection (if not auto-approved)

```bash
# List pending connections
az network private-link-service list-pe-connection \
  --resource-group $RESOURCE_GROUP \
  --name $PLS_NAME \
  --query "[?properties.privateLinkServiceConnectionState.status=='Pending'].{Name:name, Status:properties.privateLinkServiceConnectionState.status}" -o table

# Approve a connection
export PE_CONNECTION_NAME="<connection-name-from-above>"

az network private-link-service connection update \
  --resource-group $RESOURCE_GROUP \
  --service-name $PLS_NAME \
  --pe-connection-name $PE_CONNECTION_NAME \
  --connection-status Approved \
  --approval-description "Approved for production use"
```

---

## Step 9: Configure Private DNS Zone (Optional but Recommended)

```bash
# Create Private DNS Zone
export DNS_ZONE_NAME="aks-service.internal"

az network private-dns zone create \
  --resource-group $CONSUMER_RG \
  --name $DNS_ZONE_NAME

# Link DNS Zone to VNet
az network private-dns link vnet create \
  --resource-group $CONSUMER_RG \
  --zone-name $DNS_ZONE_NAME \
  --name "${CONSUMER_VNET_NAME}-link" \
  --virtual-network $CONSUMER_VNET_NAME \
  --registration-enabled false

# Create A record for the service
export PE_IP=$(az network private-endpoint show \
  --resource-group $CONSUMER_RG \
  --name $PRIVATE_ENDPOINT_NAME \
  --query "customDnsConfigs[0].ipAddresses[0]" -o tsv)

az network private-dns record-set a create \
  --resource-group $CONSUMER_RG \
  --zone-name $DNS_ZONE_NAME \
  --name "my-service"

az network private-dns record-set a add-record \
  --resource-group $CONSUMER_RG \
  --zone-name $DNS_ZONE_NAME \
  --record-set-name "my-service" \
  --ipv4-address $PE_IP
```

---

## Verification Commands

### Verify Load Balancer Configuration

```bash
# Check load balancer details
az network lb show \
  --resource-group $AKS_NODE_RG \
  --name $INTERNAL_LB_NAME \
  --query "{Name:name, FrontendIP:frontendIpConfigurations[0].privateIPAddress, Backend:backendAddressPools[0].name}" -o table

# List load balancing rules
az network lb rule list \
  --resource-group $AKS_NODE_RG \
  --lb-name $INTERNAL_LB_NAME \
  --query "[].{Name:name, FrontendPort:frontendPort, BackendPort:backendPort, Protocol:protocol}" -o table
```

### Verify Private Link Service

```bash
# Check Private Link Service status
az network private-link-service show \
  --resource-group $RESOURCE_GROUP \
  --name $PLS_NAME \
  --query "{Name:name, State:provisioningState, Alias:alias, LoadBalancer:loadBalancerFrontendIpConfigurations[0].id}" -o table

# List all Private Endpoint connections
az network private-link-service list-pe-connection \
  --resource-group $RESOURCE_GROUP \
  --name $PLS_NAME \
  --query "[].{Name:name, Status:properties.privateLinkServiceConnectionState.status, PE:properties.privateEndpoint.id}" -o table
```

### Verify Kubernetes Service

```bash
# Check service status
kubectl get service my-internal-service -o wide

# Get detailed service information
kubectl describe service my-internal-service

# Check endpoints (pods backing the service)
kubectl get endpoints my-internal-service

# Test from a pod in the cluster
kubectl run test-pod --rm -it --image=busybox --restart=Never -- wget -O- http://$LB_FRONTEND_IP
```

### Test Private Endpoint Connectivity

From a VM in the consumer VNet:

```bash
# Test connectivity via Private Endpoint IP
curl -v http://$PE_IP

# Test via DNS (if configured)
curl -v http://my-service.aks-service.internal

# Check DNS resolution
nslookup my-service.aks-service.internal
```

---

## Monitoring and Troubleshooting

### View Private Link Service Metrics

```bash
# Get connection count
az monitor metrics list \
  --resource $(az network private-link-service show \
    --resource-group $RESOURCE_GROUP \
    --name $PLS_NAME \
    --query id -o tsv) \
  --metric "BytesProcessedInbound" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --interval PT1M \
  --query "value[].timeseries[0].data[].average"
```

### Check Network Security Group Rules

```bash
# List NSG rules on the PLS subnet
export PLS_NSG=$(az network vnet subnet show \
  --resource-group $AKS_NODE_RG \
  --vnet-name $AKS_VNET_NAME \
  --name $PLS_SUBNET_NAME \
  --query "networkSecurityGroup.id" -o tsv)

if [ ! -z "$PLS_NSG" ]; then
  az network nsg show --ids $PLS_NSG
fi
```

### Debug Load Balancer Backend Pool

```bash
# Check backend pool members
az network lb address-pool list \
  --resource-group $AKS_NODE_RG \
  --lb-name $INTERNAL_LB_NAME \
  --query "[].{Name:name, BackendIPs:backendIpConfigurations[].id}" -o table
```

---

## Cleanup Commands

```bash
# Delete Private Endpoint (consumer side)
az network private-endpoint delete \
  --resource-group $CONSUMER_RG \
  --name $PRIVATE_ENDPOINT_NAME

# Delete Private Link Service
az network private-link-service delete \
  --resource-group $RESOURCE_GROUP \
  --name $PLS_NAME

# Delete Kubernetes Service
kubectl delete service my-internal-service

# Delete PLS subnet (optional)
az network vnet subnet delete \
  --resource-group $AKS_NODE_RG \
  --vnet-name $AKS_VNET_NAME \
  --name $PLS_SUBNET_NAME

# Delete Private DNS Zone (optional)
az network private-dns zone delete \
  --resource-group $CONSUMER_RG \
  --name $DNS_ZONE_NAME
```

---

## Common Issues and Solutions

### Issue 1: Load Balancer Not Created

**Symptom**: Service remains in `Pending` state.

**Solution**:
```bash
# Check service events
kubectl describe service my-internal-service

# Check AKS system logs
kubectl logs -n kube-system -l component=cloud-controller-manager --tail=100
```

### Issue 2: Private Link Service Creation Fails

**Symptom**: Error about network policies or subnet configuration.

**Solution**:
```bash
# Ensure private link service network policies are disabled
az network vnet subnet update \
  --resource-group $AKS_NODE_RG \
  --vnet-name $AKS_VNET_NAME \
  --name $PLS_SUBNET_NAME \
  --disable-private-link-service-network-policies true
```

### Issue 3: Private Endpoint Connection Pending

**Symptom**: Private Endpoint shows "Pending" status.

**Solution**: Either configure auto-approval or manually approve:
```bash
az network private-link-service connection update \
  --resource-group $RESOURCE_GROUP \
  --service-name $PLS_NAME \
  --pe-connection-name $PE_CONNECTION_NAME \
  --connection-status Approved
```

### Issue 4: Cannot Connect via Private Endpoint

**Checklist**:
1. Verify Private Endpoint is approved
2. Check NSG rules on both provider and consumer subnets
3. Verify backend pods are healthy: `kubectl get pods -l app=my-app`
4. Test load balancer directly from AKS cluster
5. Check DNS resolution if using Private DNS Zone

---

## Best Practices

1. **Use dedicated subnet for PLS**: Don't mix PLS with other resources
2. **Enable Proxy Protocol**: If you need to preserve client IP addresses
3. **Configure auto-approval**: For trusted subscriptions
4. **Set up monitoring**: Use Azure Monitor for PLS metrics
5. **Use Private DNS**: For easier service discovery
6. **Document your alias**: Store the PLS alias securely for consumers
7. **Regular health checks**: Monitor backend pool health
8. **Network policies**: Apply appropriate NSG rules

---

## Additional Resources

- [Azure Private Link Service Documentation](https://learn.microsoft.com/en-us/azure/private-link/private-link-service-overview)
- [AKS Internal Load Balancer](https://learn.microsoft.com/en-us/azure/aks/internal-lb)
- [Private Link Service with AKS](https://learn.microsoft.com/en-us/azure/aks/private-link-service)




