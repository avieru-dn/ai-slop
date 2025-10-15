# PLS Alias Survival Guide

**Problem**: When K8s Service is deleted, PLS is deleted, and the alias is lost forever.

**Solution**: Decouple PLS from K8s Service lifecycle.

---

## The Problem

```
Current (Bad):
K8s Service → Load Balancer Frontend (dynamic) → PLS (dynamic alias)
   │
   └─ DELETE → Frontend deleted → PLS deleted → Alias LOST! ❌
```

## The Solution

```
Fixed (Good):
K8s Service → Load Balancer Backend Pool ←─┐
                                            │
Static Frontend IP → PLS (permanent alias) ─┘
   │
   └─ DELETE K8s Service → Backend pool changes
                        → Frontend remains! ✅
                        → PLS remains! ✅
                        → Alias survives! ✅
```

---

## Implementation Steps

### Step 1: Apply Terraform Configuration

```bash
cd /Users/avieru/01_Work/00_GitHub/drivenets/dap-devops/terraform-k8s-setup

# Initialize
terraform init

# Review what will be created
terraform plan

# Apply (creates static frontend + persistent PLS)
terraform apply
```

**What it creates:**
1. Static Frontend IP: `10.224.5.100`
2. Load Balancing Rule: Routes traffic to Grafana pods
3. Health Probe: Monitors Grafana health
4. **Persistent PLS**: With permanent alias!

### Step 2: Get the Permanent Alias

```bash
# The alias is saved to a file
cat terraform-k8s-setup/PLS_ALIAS_PERMANENT.txt

# Or get from Terraform output
terraform output pls_alias_permanent
```

**Save this alias!** It will never change.

### Step 3: Update Consumers (One-Time)

Share the new permanent alias with all consumers:

```
Old alias (will be lost): pls-acf86472795934f6ba3f94ba5c3e567d.xxx...
New alias (permanent):    pls-grafana-persistent.yyy...westus2.azure.privatelinkservice
```

Consumers need to:
1. Delete old Private Endpoints
2. Create new Private Endpoints with new alias
3. Approve connections

### Step 4: Test Resilience

```bash
# Delete the Kubernetes service
kubectl delete svc grafana -n grafana-test

# Recreate it (via ArgoCD or kubectl)
kubectl apply -f manifests/grafana-pls/service.yaml

# Check PLS status
az network private-link-service show \
  --resource-group MC_rg-observability-aks_aks-observability_westus2 \
  --name pls-grafana-persistent \
  --query "{Name:name, Alias:alias, State:provisioningState}"

# Result: PLS still exists! Alias unchanged! ✅
```

---

## How It Works

### Architecture

```
┌──────────────────────────────────────────────────────────┐
│ Kubernetes Service (can be deleted/recreated)            │
│ name: grafana                                            │
│ type: LoadBalancer                                       │
└────────────┬─────────────────────────────────────────────┘
             │
             │ Pods registered to backend pool
             ▼
┌──────────────────────────────────────────────────────────┐
│ Load Balancer: kubernetes-internal                       │
│                                                          │
│ Backend Pool: kubernetes                                 │
│ ├── Grafana Pod 1 (10.224.0.161)                       │
│ ├── Grafana Pod 2 (10.224.0.162)                       │
│ └── Grafana Pod 3 (10.224.0.163)                       │
│                                                          │
│ ┌────────────────────────────────────────────────┐     │
│ │ Static Frontend IP (managed by Terraform)       │     │
│ │ Name: grafana-pls-static-frontend              │     │
│ │ IP: 10.224.5.100                               │     │
│ │ Lifecycle: Independent of K8s service!          │     │
│ └──────────────┬─────────────────────────────────┘     │
└────────────────┼──────────────────────────────────────────┘
                 │
                 │ Load Balancing Rule
                 │ Port 3000 → Backend Pool
                 │
                 ▼
┌──────────────────────────────────────────────────────────┐
│ Private Link Service                                     │
│ Name: pls-grafana-persistent                            │
│ Alias: pls-grafana-persistent.xxx.westus2.azure...     │
│ ├── Connected to: Static Frontend IP                    │
│ └── Lifecycle: Protected by Terraform!                  │
└──────────────────────────────────────────────────────────┘
```

### Traffic Flow

```
Consumer → Private Endpoint
              ↓
         Private Link
              ↓
         PLS (10.224.5.100)
              ↓
         Static Frontend IP
              ↓
         Load Balancing Rule
              ↓
         Backend Pool
              ↓
         Grafana Pod
```

---

## Maintenance

### Updating Grafana Service

```bash
# You can freely update/delete/recreate the service
kubectl delete svc grafana -n grafana-test
kubectl apply -f new-grafana-service.yaml

# PLS and alias remain untouched! ✅
```

### Updating PLS Configuration

```hcl
# terraform-k8s-setup/grafana-pls-persistent.tf

# Change visibility
resource "azurerm_private_link_service" "grafana_persistent" {
  # ...
  
  visibility_subscription_ids = [
    "00e10e35-0ad0-427e-893a-72f3b42387c1",
    "new-subscription-id-here"
  ]
}
```

```bash
terraform apply  # Updates PLS, alias stays the same!
```

### Checking PLS Status

```bash
# Quick check
az network private-link-service show \
  --resource-group MC_rg-observability-aks_aks-observability_westus2 \
  --name pls-grafana-persistent \
  --output table

# Get alias
terraform output pls_alias_permanent

# Check Private Endpoint connections
az network private-link-service show \
  --resource-group MC_rg-observability-aks_aks-observability_westus2 \
  --name pls-grafana-persistent \
  --query "privateEndpointConnections[].{Name:name, Status:privateLinkServiceConnectionState.status}"
```

---

## Troubleshooting

### Issue: PLS Not Routing Traffic

**Symptom**: Private Endpoints connected but no traffic flowing

**Check 1**: Verify load balancing rule exists
```bash
az network lb rule show \
  --resource-group MC_rg-observability-aks_aks-observability_westus2 \
  --lb-name kubernetes-internal \
  --name grafana-static-lb-rule
```

**Check 2**: Verify backend pool has members
```bash
az network lb address-pool show \
  --resource-group MC_rg-observability-aks_aks-observability_westus2 \
  --lb-name kubernetes-internal \
  --name kubernetes \
  --query "backendIPConfigurations[].{IP:privateIPAddress}"
```

**Check 3**: Test from within VNet
```bash
kubectl run test --image=curlimages/curl -it --rm -- curl http://10.224.5.100:3000
```

---

### Issue: Health Probe Failing

**Symptom**: Load balancer not routing to pods

**Solution**: Check health probe configuration
```bash
az network lb probe show \
  --resource-group MC_rg-observability-aks_aks-observability_westus2 \
  --lb-name kubernetes-internal \
  --name grafana-health-probe
```

Ensure Grafana is listening on port 3000:
```bash
kubectl exec -it -n grafana-test <grafana-pod> -- netstat -ln | grep 3000
```

---

### Issue: Terraform State Drift

**Symptom**: Terraform wants to recreate resources

**Solution**: Import existing resources
```bash
# Import load balancer frontend IP
terraform import azurerm_lb_frontend_ip_configuration.grafana_static \
  /subscriptions/.../resourceGroups/.../providers/Microsoft.Network/loadBalancers/kubernetes-internal/frontendIPConfigurations/grafana-pls-static-frontend

# Import PLS
terraform import azurerm_private_link_service.grafana_persistent \
  /subscriptions/.../resourceGroups/.../providers/Microsoft.Network/privateLinkServices/pls-grafana-persistent
```

---

## Migration from Current Setup

### Current State
- PLS: `pls-acf86472795934f6ba3f94ba5c3e567d`
- Alias: `pls-acf86472795934f6ba3f94ba5c3e567d.f8fe5950-a529-401c-9fcd-6b7ab916e175.westus2.azure.privatelinkservice`
- Consumers: Private Endpoint `pe-avieru-test-grafana` (10.238.0.4)

### Migration Steps

1. **Apply Terraform** (creates new persistent PLS)
   ```bash
   cd terraform-k8s-setup
   terraform apply
   ```

2. **Get new alias**
   ```bash
   NEW_ALIAS=$(terraform output -raw pls_alias_permanent)
   echo "New alias: $NEW_ALIAS"
   ```

3. **Update Private Endpoint** (test PE)
   ```bash
   # Delete old PE
   az network private-endpoint delete \
     --name pe-avieru-test-grafana \
     --resource-group MC_rg-observability-aks_aks-observability_westus2
   
   # Create new PE with persistent alias
   az network private-endpoint create \
     --name pe-avieru-test-grafana-v2 \
     --resource-group MC_rg-observability-aks_aks-observability_westus2 \
     --vnet-name aks-vnet-38705521 \
     --subnet aks-appgateway \
     --connection-name grafana-persistent-connection \
     --manual-request true \
     --private-connection-resource-id "/subscriptions/00e10e35-0ad0-427e-893a-72f3b42387c1/resourceGroups/MC_rg-observability-aks_aks-observability_westus2/providers/Microsoft.Network/privateLinkServices/pls-grafana-persistent"
   ```

4. **Approve connection**
   ```bash
   # In Azure Portal or CLI
   az network private-link-service show \
     --resource-group MC_rg-observability-aks_aks-observability_westus2 \
     --name pls-grafana-persistent \
     --query "privateEndpointConnections"
   ```

5. **Test connectivity**
   ```bash
   # Get new PE IP
   NEW_PE_IP=$(az network nic show \
     --resource-group MC_rg-observability-aks_aks-observability_westus2 \
     --name pe-avieru-test-grafana-v2-nic \
     --query "ipConfigurations[0].privateIPAddress" \
     --output tsv)
   
   # Test
   kubectl exec -it -n grafana-test <grafana-pod> -- curl http://$NEW_PE_IP:3000
   ```

6. **Cleanup old PLS** (optional)
   ```bash
   # Once all consumers migrated
   az network private-link-service delete \
     --name pls-acf86472795934f6ba3f94ba5c3e567d \
     --resource-group MC_rg-observability-aks_aks-observability_westus2
   ```

---

## Best Practices

### 1. Document the Alias

Create a record in your repository:

```yaml
# docs/pls-aliases.yaml
production:
  grafana:
    pls_name: pls-grafana-persistent
    alias: pls-grafana-persistent.xxx.westus2.azure.privatelinkservice
    static_ip: 10.224.5.100
    created: 2025-10-14
    terraform_managed: true
    consumers:
      - name: DAP_Dev
        subscription: cda76fc5-a3ee-4c98-b4ba-055125b3de93
        private_endpoint: pe-grafana-dev
      - name: Internal Testing
        subscription: 00e10e35-0ad0-427e-893a-72f3b42387c1
        private_endpoint: pe-avieru-test-grafana-v2
```

### 2. Monitor PLS Health

```bash
# Create alert for PLS deletion
az monitor metrics alert create \
  --name "PLS-Grafana-Deleted" \
  --resource /subscriptions/.../privateLinkServices/pls-grafana-persistent \
  --condition "count ResourceHealth > 0" \
  --description "Alert if PLS is deleted"
```

### 3. Backup Terraform State

```bash
# Use remote state
terraform {
  backend "azurerm" {
    resource_group_name  = "terraform-state-rg"
    storage_account_name = "tfstatedapdevops"
    container_name       = "tfstate"
    key                  = "grafana-pls.tfstate"
  }
}
```

### 4. Test Regularly

```bash
# Monthly test: Delete and recreate service
kubectl delete svc grafana -n grafana-test
kubectl apply -f manifests/grafana-pls/service.yaml

# Verify PLS still works
az network private-link-service show \
  --name pls-grafana-persistent \
  --resource-group MC_rg-observability-aks_aks-observability_westus2 \
  --query "alias"

# Test from PE
kubectl exec -it -n grafana-test <pod> -- curl http://<PE-IP>:3000
```

---

## Summary

✅ **What This Solves:**
- PLS alias is permanent (survives service deletion)
- No need to update consumers when service changes
- Terraform-managed (reproducible, version-controlled)
- Protected from accidental deletion

✅ **What You Can Do:**
- Delete/recreate Kubernetes service freely
- Upgrade via Helm uninstall/install
- Service disruptions don't affect PLS
- Alias never changes

❌ **What You Cannot Do:**
- Delete the static frontend IP (Terraform protects it)
- Delete PLS without Terraform (prevent_destroy = true)
- Change the static IP without updating consumers

---

## Quick Reference

```bash
# Get permanent alias
terraform output pls_alias_permanent

# Check PLS status
az network private-link-service show \
  --name pls-grafana-persistent \
  --resource-group MC_rg-observability-aks_aks-observability_westus2

# Test from PE
kubectl run test --image=curlimages/curl -it --rm -- curl http://<PE-IP>:3000

# View Terraform state
terraform show

# Update PLS configuration
terraform apply
```

---

**Result**: Your PLS alias is now immortal! 🎉


