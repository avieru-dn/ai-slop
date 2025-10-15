# AKS Internal Load Balancer Guide

**Cluster**: aks-observability (West US 2)  
**VNet**: aks-vnet-38705521 (10.224.0.0/12)  
**Subnet**: aks-subnet (10.224.0.0/16)  
**Created**: October 14, 2025

---

## Table of Contents
1. [Overview](#overview)
2. [Internal Load Balancer Basics](#internal-load-balancer-basics)
3. [Prerequisites](#prerequisites)
4. [Quick Start Examples](#quick-start-examples)
5. [Configuration Options](#configuration-options)
6. [Advanced Scenarios](#advanced-scenarios)
7. [Troubleshooting](#troubleshooting)

---

## Overview

An **Internal Load Balancer (ILB)** in Azure Kubernetes Service exposes services within your Azure Virtual Network, making them accessible only to:
- Resources within the same VNet
- Peered VNets
- On-premises networks connected via VPN/ExpressRoute

**Use Cases for Internal Load Balancer:**
- ✅ Internal APIs and microservices
- ✅ Database endpoints (PostgreSQL, Redis, etc.)
- ✅ Observability tools (Prometheus, Grafana, VictoriaMetrics)
- ✅ Admin dashboards and internal tools
- ✅ Private endpoints for multi-cluster communication

**Current Environment:**
- **Cluster**: `aks-observability`
- **VNet**: `10.224.0.0/12`
- **Node Subnet**: `10.224.0.0/16`

---

## Internal Load Balancer Basics

### Public vs Internal Load Balancer

| Feature | Public LB | Internal LB |
|---------|-----------|-------------|
| **IP Assignment** | Public IP from Azure | Private IP from VNet |
| **Accessibility** | Internet-accessible | VNet-only (or peered VNets) |
| **Use Case** | External services | Internal/private services |
| **Security** | Requires NSG/firewall rules | Network-isolated by default |
| **Cost** | Public IP charges apply | No public IP charges |

### How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                    Azure Virtual Network                     │
│                      10.224.0.0/12                          │
│                                                              │
│  ┌──────────────────────────────────────────────────┐      │
│  │           Internal Load Balancer                  │      │
│  │         Private IP: 10.224.5.100                  │      │
│  │         (from aks-subnet)                         │      │
│  └──────────────┬───────────────────┬────────────────┘      │
│                 │                   │                        │
│      ┏━━━━━━━━━━▼━━━━━━━━┓  ┏━━━━━━▼━━━━━━━━┓             │
│      ┃   Pod 1           ┃  ┃   Pod 2        ┃             │
│      ┃   10.224.10.5     ┃  ┃   10.224.10.6  ┃             │
│      ┃   app:grafana     ┃  ┃   app:grafana  ┃             │
│      ┗━━━━━━━━━━━━━━━━━━━┛  ┗━━━━━━━━━━━━━━━━┛             │
│                                                              │
│  Accessible from:                                            │
│  • Other pods in the cluster                                 │
│  • VMs in the same VNet or peered VNets                      │
│  • On-premises via VPN/ExpressRoute                          │
│                                                              │
│  NOT accessible from:                                        │
│  • Public internet                                           │
│  • Non-peered VNets                                          │
└─────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### 1. Verify Cluster Access
```bash
# Set the subscription
az account set --subscription "00e10e35-0ad0-427e-893a-72f3b42387c1"

# Get credentials
az aks get-credentials \
  --resource-group rg-observability-aks \
  --name aks-observability \
  --overwrite-existing

# Verify access
kubectl get nodes
```

### 2. Verify Network Configuration
```bash
# Check VNet details
az network vnet show \
  --resource-group MC_rg-observability-aks_aks-observability_westus2 \
  --name aks-vnet-38705521 \
  --query "{Name:name, AddressSpace:addressSpace.addressPrefixes}" \
  --output table

# Check subnet details
az network vnet subnet list \
  --resource-group MC_rg-observability-aks_aks-observability_westus2 \
  --vnet-name aks-vnet-38705521 \
  --query "[].{Name:name, AddressPrefix:addressPrefix}" \
  --output table
```

### 3. Check Required Permissions
The AKS cluster's managed identity needs:
- `Network Contributor` role on the VNet/subnet
- Ability to create load balancers in the node resource group

```bash
# Verify cluster identity has permissions
az aks show \
  --resource-group rg-observability-aks \
  --name aks-observability \
  --query "identity.principalId" \
  --output tsv
```

---

## Quick Start Examples

### Example 1: Basic Internal Load Balancer Service

```yaml
# basic-internal-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: my-internal-service
  namespace: default
  annotations:
    # KEY ANNOTATION: This makes it internal
    service.beta.kubernetes.io/azure-load-balancer-internal: "true"
spec:
  type: LoadBalancer
  selector:
    app: my-app
  ports:
    - name: http
      protocol: TCP
      port: 80
      targetPort: 8080
```

**Deploy:**
```bash
kubectl apply -f basic-internal-service.yaml

# Check the service
kubectl get svc my-internal-service

# Get the internal IP
kubectl get svc my-internal-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

**Expected Output:**
```
NAME                   TYPE           CLUSTER-IP     EXTERNAL-IP    PORT(S)        AGE
my-internal-service    LoadBalancer   10.0.154.23    10.224.5.100   80:31234/TCP   2m
```

Note: The `EXTERNAL-IP` is actually a **private IP** from your VNet (10.224.x.x range).

---

### Example 2: Internal Service with Specific Subnet

If you want to use a specific subnet (not the default node subnet):

```yaml
# internal-service-specific-subnet.yaml
apiVersion: v1
kind: Service
metadata:
  name: grafana-internal
  namespace: monitoring
  annotations:
    service.beta.kubernetes.io/azure-load-balancer-internal: "true"
    # Specify a different subnet for the load balancer IP
    service.beta.kubernetes.io/azure-load-balancer-internal-subnet: "aks-appgateway"
spec:
  type: LoadBalancer
  selector:
    app: grafana
  ports:
    - name: web
      protocol: TCP
      port: 3000
      targetPort: 3000
```

**Result:** Load balancer IP will be allocated from `10.238.0.0/24` subnet instead of the default node subnet.

---

### Example 3: Internal Service with Static IP

```yaml
# internal-service-static-ip.yaml
apiVersion: v1
kind: Service
metadata:
  name: victoriametrics-internal
  namespace: monitoring
  annotations:
    service.beta.kubernetes.io/azure-load-balancer-internal: "true"
spec:
  type: LoadBalancer
  # Specify a static IP from your subnet range
  loadBalancerIP: 10.224.5.200
  selector:
    app: victoriametrics
  ports:
    - name: http
      protocol: TCP
      port: 8428
      targetPort: 8428
```

**Important:** Ensure the IP address:
- ✅ Is within the subnet range (10.224.0.0/16)
- ✅ Is not already in use
- ✅ Is not in the Kubernetes service CIDR range

---

### Example 4: Real-World - Grafana Internal Access

```yaml
# grafana-internal-lb.yaml
apiVersion: v1
kind: Service
metadata:
  name: grafana-internal
  namespace: monitoring
  annotations:
    service.beta.kubernetes.io/azure-load-balancer-internal: "true"
    service.beta.kubernetes.io/azure-load-balancer-internal-subnet: "aks-subnet"
    # Optional: Set session affinity for better UX
    service.beta.kubernetes.io/azure-load-balancer-enable-high-availability: "true"
  labels:
    app: grafana
    component: observability
spec:
  type: LoadBalancer
  sessionAffinity: ClientIP
  sessionAffinityConfig:
    clientIP:
      timeoutSeconds: 10800  # 3 hours
  selector:
    app.kubernetes.io/name: grafana
  ports:
    - name: web
      protocol: TCP
      port: 80
      targetPort: 3000
```

**Deploy and Verify:**
```bash
kubectl apply -f grafana-internal-lb.yaml

# Wait for IP assignment
kubectl wait --for=jsonpath='{.status.loadBalancer.ingress}' \
  service/grafana-internal -n monitoring --timeout=300s

# Get the internal IP
GRAFANA_INTERNAL_IP=$(kubectl get svc grafana-internal -n monitoring \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

echo "Grafana is accessible at: http://${GRAFANA_INTERNAL_IP}"
```

---

### Example 5: VictoriaMetrics with Multiple Ports

```yaml
# victoriametrics-internal-lb.yaml
apiVersion: v1
kind: Service
metadata:
  name: victoriametrics-internal
  namespace: monitoring
  annotations:
    service.beta.kubernetes.io/azure-load-balancer-internal: "true"
    # Add resource tags for cost tracking
    service.beta.kubernetes.io/azure-load-balancer-resource-group: "MC_rg-observability-aks_aks-observability_westus2"
spec:
  type: LoadBalancer
  loadBalancerIP: 10.224.5.150
  selector:
    app.kubernetes.io/name: victoria-metrics-single
  ports:
    - name: http
      protocol: TCP
      port: 8428
      targetPort: 8428
    - name: metrics
      protocol: TCP
      port: 8089
      targetPort: 8089
```

---

## Configuration Options

### Available Annotations

| Annotation | Purpose | Example Value |
|------------|---------|---------------|
| `service.beta.kubernetes.io/azure-load-balancer-internal` | **Enable internal LB** | `"true"` |
| `service.beta.kubernetes.io/azure-load-balancer-internal-subnet` | Specify subnet | `"aks-appgateway"` |
| `service.beta.kubernetes.io/azure-load-balancer-resource-group` | Target resource group | `"MC_rg-..._westus2"` |
| `service.beta.kubernetes.io/azure-pip-tags` | Add tags to resources | `"Environment=prod,Owner=sre"` |
| `service.beta.kubernetes.io/azure-load-balancer-enable-high-availability` | Enable HA ports | `"true"` |
| `service.beta.kubernetes.io/azure-load-balancer-health-probe-interval` | Health check interval | `"5"` (seconds) |
| `service.beta.kubernetes.io/azure-load-balancer-health-probe-num-of-probe` | Health check retries | `"2"` |
| `service.beta.kubernetes.io/azure-load-balancer-tcp-idle-timeout` | TCP timeout | `"4"` (minutes) |

### Load Balancer SKUs

Azure supports two SKUs:
- **Basic** (deprecated, don't use)
- **Standard** (recommended, default in modern AKS)

Check your cluster's LB SKU:
```bash
az aks show \
  --resource-group rg-observability-aks \
  --name aks-observability \
  --query "networkProfile.loadBalancerSku" \
  --output tsv
```

---

## Advanced Scenarios

### Scenario 1: Internal LB with Custom Health Probe

```yaml
apiVersion: v1
kind: Service
metadata:
  name: api-internal
  namespace: production
  annotations:
    service.beta.kubernetes.io/azure-load-balancer-internal: "true"
    # Custom health probe configuration
    service.beta.kubernetes.io/azure-load-balancer-health-probe-interval: "5"
    service.beta.kubernetes.io/azure-load-balancer-health-probe-num-of-probe: "2"
    service.beta.kubernetes.io/azure-load-balancer-health-probe-request-path: "/healthz"
spec:
  type: LoadBalancer
  externalTrafficPolicy: Local  # Preserve source IP
  selector:
    app: api-server
  ports:
    - name: https
      protocol: TCP
      port: 443
      targetPort: 8443
```

**Benefits of `externalTrafficPolicy: Local`:**
- ✅ Preserves client source IP address
- ✅ Reduces extra network hop
- ⚠️ May cause uneven load distribution

---

### Scenario 2: Multiple Internal Load Balancers

You can create multiple internal services, each with its own IP:

```yaml
---
apiVersion: v1
kind: Service
metadata:
  name: prometheus-internal
  namespace: monitoring
  annotations:
    service.beta.kubernetes.io/azure-load-balancer-internal: "true"
spec:
  type: LoadBalancer
  loadBalancerIP: 10.224.5.10
  selector:
    app: prometheus
  ports:
    - port: 9090
      targetPort: 9090
---
apiVersion: v1
kind: Service
metadata:
  name: alertmanager-internal
  namespace: monitoring
  annotations:
    service.beta.kubernetes.io/azure-load-balancer-internal: "true"
spec:
  type: LoadBalancer
  loadBalancerIP: 10.224.5.11
  selector:
    app: alertmanager
  ports:
    - port: 9093
      targetPort: 9093
---
apiVersion: v1
kind: Service
metadata:
  name: loki-internal
  namespace: monitoring
  annotations:
    service.beta.kubernetes.io/azure-load-balancer-internal: "true"
spec:
  type: LoadBalancer
  loadBalancerIP: 10.224.5.12
  selector:
    app: loki
  ports:
    - port: 3100
      targetPort: 3100
```

---

### Scenario 3: Cross-Cluster Access via Internal LB

Enable services in `aks-observability` to be accessed from other clusters:

**Step 1: Create internal service in observability cluster**
```yaml
# In aks-observability cluster
apiVersion: v1
kind: Service
metadata:
  name: shared-prometheus
  namespace: monitoring
  annotations:
    service.beta.kubernetes.io/azure-load-balancer-internal: "true"
spec:
  type: LoadBalancer
  loadBalancerIP: 10.224.5.50
  selector:
    app: prometheus
  ports:
    - name: http
      port: 9090
      targetPort: 9090
```

**Step 2: Peer VNets** (if not already peered)
```bash
# From aks-dev VNet to aks-observability VNet
az network vnet peering create \
  --name dev-to-observability \
  --resource-group MC_dev_aks-dev_westus2 \
  --vnet-name aks-vnet-10099729 \
  --remote-vnet /subscriptions/00e10e35-0ad0-427e-893a-72f3b42387c1/resourceGroups/MC_rg-observability-aks_aks-observability_westus2/providers/Microsoft.Network/virtualNetworks/aks-vnet-38705521 \
  --allow-vnet-access

# Reverse peering
az network vnet peering create \
  --name observability-to-dev \
  --resource-group MC_rg-observability-aks_aks-observability_westus2 \
  --vnet-name aks-vnet-38705521 \
  --remote-vnet /subscriptions/cda76fc5-a3ee-4c98-b4ba-055125b3de93/resourceGroups/MC_dev_aks-dev_westus2/providers/Microsoft.Network/virtualNetworks/aks-vnet-10099729 \
  --allow-vnet-access
```

**Note:** ⚠️ You currently have **IP address conflicts** (10.224.0.0/12 is used by multiple clusters). Resolve this before peering!

**Step 3: Access from another cluster**
```yaml
# In aks-dev cluster - configure remote Prometheus
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
data:
  prometheus.yml: |
    remote_read:
      - url: http://10.224.5.50:9090/api/v1/read
    remote_write:
      - url: http://10.224.5.50:9090/api/v1/write
```

---

### Scenario 4: Internal LB with Private Link Service

For even more controlled access, combine Internal LB with Azure Private Link:

```yaml
# Step 1: Create internal LB service
apiVersion: v1
kind: Service
metadata:
  name: api-for-private-link
  namespace: production
  annotations:
    service.beta.kubernetes.io/azure-load-balancer-internal: "true"
    # Disable private link service network policies
    service.beta.kubernetes.io/azure-pls-create: "true"
    service.beta.kubernetes.io/azure-pls-name: "api-private-link"
    service.beta.kubernetes.io/azure-pls-ip-configuration-subnet: "aks-subnet"
spec:
  type: LoadBalancer
  loadBalancerIP: 10.224.5.100
  selector:
    app: api
  ports:
    - port: 443
      targetPort: 8443
```

See: [Azure Private Link Service Guide](./azure-private-link-service-guide.md) for detailed setup.

---

## Troubleshooting

### Issue 1: Service Stuck in "Pending"

**Symptom:**
```bash
$ kubectl get svc my-service
NAME         TYPE           CLUSTER-IP    EXTERNAL-IP   PORT(S)        AGE
my-service   LoadBalancer   10.0.154.23   <pending>     80:31234/TCP   5m
```

**Diagnosis:**
```bash
# Check service events
kubectl describe svc my-service

# Check cloud provider logs
kubectl logs -n kube-system -l component=cloud-controller-manager --tail=100
```

**Common Causes & Solutions:**

**Cause 1: Missing annotation**
```yaml
# ❌ WRONG - Missing internal annotation
spec:
  type: LoadBalancer

# ✅ CORRECT
metadata:
  annotations:
    service.beta.kubernetes.io/azure-load-balancer-internal: "true"
```

**Cause 2: Invalid subnet name**
```bash
# Verify subnet exists
az network vnet subnet list \
  --resource-group MC_rg-observability-aks_aks-observability_westus2 \
  --vnet-name aks-vnet-38705521 \
  --query "[].name" \
  --output tsv
```

**Cause 3: IP address already in use**
```bash
# Check if IP is available
az network lb list \
  --resource-group MC_rg-observability-aks_aks-observability_westus2 \
  --query "[].frontendIpConfigurations[].privateIpAddress" \
  --output tsv
```

**Cause 4: Insufficient permissions**
```bash
# Verify cluster identity has Network Contributor role
CLUSTER_IDENTITY=$(az aks show \
  --resource-group rg-observability-aks \
  --name aks-observability \
  --query "identity.principalId" \
  --output tsv)

az role assignment list \
  --assignee $CLUSTER_IDENTITY \
  --query "[?roleDefinitionName=='Network Contributor']" \
  --output table
```

---

### Issue 2: Cannot Access Internal IP

**Symptom:**
Service has an internal IP, but cannot reach it from other resources.

**Diagnosis Steps:**

**1. Verify you're in the same VNet or peered VNet:**
```bash
# Check if source and destination are in same/peered VNet
az network vnet peering list \
  --resource-group MC_rg-observability-aks_aks-observability_westus2 \
  --vnet-name aks-vnet-38705521 \
  --output table
```

**2. Check Network Security Groups (NSGs):**
```bash
# List NSGs in the node resource group
az network nsg list \
  --resource-group MC_rg-observability-aks_aks-observability_westus2 \
  --output table

# Check NSG rules
az network nsg rule list \
  --resource-group MC_rg-observability-aks_aks-observability_westus2 \
  --nsg-name <nsg-name> \
  --output table
```

**3. Test connectivity from a pod in the cluster:**
```bash
# Create a test pod
kubectl run test-connectivity --image=busybox -it --rm -- sh

# Inside the pod, test the internal IP
wget -O- http://10.224.5.100:80
```

**4. Test from a VM in the same VNet:**
```bash
# SSH to a VM in the VNet and test
curl http://10.224.5.100:80
```

**5. Check pod endpoints:**
```bash
# Verify pods are running and ready
kubectl get pods -l app=my-app

# Check endpoints
kubectl get endpoints my-service
```

---

### Issue 3: Source IP Not Preserved

**Symptom:**
Application sees cluster internal IPs instead of client IPs.

**Solution:**
```yaml
spec:
  type: LoadBalancer
  externalTrafficPolicy: Local  # Add this line
```

**Trade-offs:**
- ✅ Preserves source IP
- ✅ Reduces one network hop
- ⚠️ May cause uneven load distribution (only nodes with pods receive traffic)
- ⚠️ Health checks happen at node level

---

### Issue 4: High Latency or Connection Issues

**Cause:** Default TCP idle timeout is 4 minutes.

**Solution:** Increase timeout
```yaml
metadata:
  annotations:
    service.beta.kubernetes.io/azure-load-balancer-internal: "true"
    service.beta.kubernetes.io/azure-load-balancer-tcp-idle-timeout: "30"  # 30 minutes
```

---

## Production Best Practices

### 1. Use Terraform/IaC for Service Management

```hcl
# terraform/observability/internal-services.tf
resource "kubernetes_service" "grafana_internal" {
  metadata {
    name      = "grafana-internal"
    namespace = "monitoring"
    
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
    
    load_balancer_ip = "10.224.5.100"
    
    session_affinity = "ClientIP"
    
    port {
      name        = "web"
      protocol    = "TCP"
      port        = 80
      target_port = 3000
    }
    
    selector = {
      "app.kubernetes.io/name" = "grafana"
    }
  }
}

output "grafana_internal_ip" {
  value       = kubernetes_service.grafana_internal.status[0].load_balancer[0].ingress[0].ip
  description = "Internal IP for Grafana"
}
```

---

### 2. Document Internal IPs

Create an IP allocation tracking document:

```yaml
# docs/internal-lb-allocations.yaml
internal_load_balancers:
  aks-observability:
    vnet: "10.224.0.0/12"
    subnet: "aks-subnet (10.224.0.0/16)"
    reserved_range: "10.224.5.0/24"
    
    allocations:
      - ip: "10.224.5.10"
        service: "prometheus-internal"
        namespace: "monitoring"
        port: 9090
        
      - ip: "10.224.5.11"
        service: "alertmanager-internal"
        namespace: "monitoring"
        port: 9093
        
      - ip: "10.224.5.12"
        service: "loki-internal"
        namespace: "monitoring"
        port: 3100
        
      - ip: "10.224.5.50"
        service: "grafana-internal"
        namespace: "monitoring"
        port: 80
        
      - ip: "10.224.5.100"
        service: "victoriametrics-internal"
        namespace: "monitoring"
        port: 8428
```

---

### 3. Implement Monitoring

```yaml
# prometheus-servicemonitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: internal-loadbalancer-metrics
  namespace: monitoring
spec:
  selector:
    matchLabels:
      component: observability
  endpoints:
    - port: metrics
      interval: 30s
```

**Monitor these metrics:**
- Load balancer health probe status
- Backend pool health
- Connection count
- Throughput
- Latency

---

### 4. Security Considerations

**Network Policies:**
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-internal-lb-traffic
  namespace: monitoring
spec:
  podSelector:
    matchLabels:
      app: grafana
  policyTypes:
    - Ingress
  ingress:
    - from:
        # Allow traffic from specific IP ranges
        - ipBlock:
            cidr: 10.224.0.0/12
      ports:
        - protocol: TCP
          port: 3000
```

**Azure NSG Rules:**
```bash
# Add NSG rule to allow traffic from specific subnets
az network nsg rule create \
  --resource-group MC_rg-observability-aks_aks-observability_westus2 \
  --nsg-name <nsg-name> \
  --name allow-internal-lb-traffic \
  --priority 100 \
  --source-address-prefixes 10.224.0.0/16 \
  --destination-port-ranges 80 443 \
  --access Allow \
  --protocol Tcp
```

---

## Complete Real-World Example

Here's a complete setup for the observability stack:

```yaml
# observability-internal-services.yaml
---
apiVersion: v1
kind: Service
metadata:
  name: grafana-internal
  namespace: monitoring
  annotations:
    service.beta.kubernetes.io/azure-load-balancer-internal: "true"
    service.beta.kubernetes.io/azure-load-balancer-internal-subnet: "aks-subnet"
  labels:
    app: grafana
    component: observability
    exposure: internal
spec:
  type: LoadBalancer
  loadBalancerIP: 10.224.5.50
  sessionAffinity: ClientIP
  sessionAffinityConfig:
    clientIP:
      timeoutSeconds: 10800
  selector:
    app.kubernetes.io/name: grafana
  ports:
    - name: web
      protocol: TCP
      port: 80
      targetPort: 3000

---
apiVersion: v1
kind: Service
metadata:
  name: victoriametrics-internal
  namespace: monitoring
  annotations:
    service.beta.kubernetes.io/azure-load-balancer-internal: "true"
    service.beta.kubernetes.io/azure-load-balancer-tcp-idle-timeout: "30"
  labels:
    app: victoriametrics
    component: observability
spec:
  type: LoadBalancer
  loadBalancerIP: 10.224.5.100
  selector:
    app.kubernetes.io/name: victoria-metrics-single
  ports:
    - name: http
      protocol: TCP
      port: 8428
      targetPort: 8428

---
apiVersion: v1
kind: Service
metadata:
  name: victorialogs-internal
  namespace: monitoring
  annotations:
    service.beta.kubernetes.io/azure-load-balancer-internal: "true"
  labels:
    app: victorialogs
    component: observability
spec:
  type: LoadBalancer
  loadBalancerIP: 10.224.5.150
  selector:
    app.kubernetes.io/name: victoria-logs
  ports:
    - name: http
      protocol: TCP
      port: 9428
      targetPort: 9428
```

**Deploy:**
```bash
kubectl apply -f observability-internal-services.yaml

# Wait for all IPs to be assigned
kubectl wait --for=jsonpath='{.status.loadBalancer.ingress}' \
  service/grafana-internal \
  service/victoriametrics-internal \
  service/victorialogs-internal \
  -n monitoring --timeout=300s

# Display all internal IPs
kubectl get svc -n monitoring -o custom-columns=NAME:.metadata.name,INTERNAL-IP:.status.loadBalancer.ingress[0].ip
```

---

## Verification & Testing

### Test Internal Connectivity

```bash
# Test from within the cluster
kubectl run curl-test --image=curlimages/curl -it --rm -- sh

# Inside the pod:
curl http://10.224.5.50       # Grafana
curl http://10.224.5.100:8428/metrics  # VictoriaMetrics
curl http://10.224.5.150:9428/health   # VictoriaLogs
```

### Test from Peered VNet (Future)

Once VNet peering is configured:
```bash
# From a VM or another AKS cluster in a peered VNet
curl http://10.224.5.50
```

---

## Related Documentation

- [Azure Private Link Service Guide](./azure-private-link-service-guide.md)
- [VNet Analysis and Risks](./vnet-analysis-and-risks.md)
- [AKS Network Concepts](https://learn.microsoft.com/azure/aks/concepts-network)
- [Azure Load Balancer](https://learn.microsoft.com/azure/load-balancer/load-balancer-overview)

---

## Quick Reference Commands

```bash
# Get all internal load balancer IPs
kubectl get svc --all-namespaces -o json | \
  jq -r '.items[] | select(.metadata.annotations["service.beta.kubernetes.io/azure-load-balancer-internal"]=="true") | "\(.metadata.name) (\(.metadata.namespace)): \(.status.loadBalancer.ingress[0].ip)"'

# List Azure load balancers created by AKS
az network lb list \
  --resource-group MC_rg-observability-aks_aks-observability_westus2 \
  --query "[].{Name:name, IP:frontendIpConfigurations[0].privateIpAddress}" \
  --output table

# Check load balancer backend pools
az network lb address-pool list \
  --resource-group MC_rg-observability-aks_aks-observability_westus2 \
  --lb-name kubernetes-internal \
  --output table

# Delete internal service (will remove LB)
kubectl delete svc <service-name> -n <namespace>
```

---

**Document Owner**: DevOps/SRE Team  
**Last Updated**: October 14, 2025  
**Cluster**: aks-observability (West US 2)


