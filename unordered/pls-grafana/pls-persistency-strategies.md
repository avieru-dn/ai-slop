# Private Link Service Persistency Strategies

**Problem**: If the Kubernetes Service is deleted, the Private Link Service is also deleted.

**Question**: How to ensure persistency?

---

## Strategy Comparison

| Strategy | Persistency | Complexity | Recovery Time | Best For |
|----------|-------------|------------|---------------|----------|
| **1. Infrastructure as Code (Terraform)** | ⭐⭐⭐⭐⭐ | Medium | Minutes | Production |
| **2. Helm Charts** | ⭐⭐⭐⭐ | Low | Minutes | Standard deployments |
| **3. GitOps (ArgoCD/Flux)** | ⭐⭐⭐⭐⭐ | Medium | Seconds | Auto-healing |
| **4. Backup & Documentation** | ⭐⭐⭐ | Low | Manual | Small setups |
| **5. Resource Protection** | ⭐⭐ | Low | N/A | Prevention only |

---

## Strategy 1: Infrastructure as Code (Terraform) ⭐⭐⭐⭐⭐

**Best for**: Production environments, team collaboration

### ✅ Pros:
- Complete infrastructure definition
- Version controlled
- Reproducible
- Can recreate entire stack in minutes
- Handles dependencies automatically
- Team collaboration via remote state

### Implementation:

See the Terraform module created at: `terraform-k8s-setup/modules/grafana-pls/`

**Usage**:
```bash
cd terraform-k8s-setup
terraform init
terraform apply

# If service gets deleted
terraform apply  # Recreates everything!
```

**Benefits**:
```
Delete Service → terraform apply → Everything recreated ✅
- Service
- Load Balancer
- Private Link Service
- All configurations
```

---

## Strategy 2: Helm Charts ⭐⭐⭐⭐

**Best for**: Kubernetes-native deployments

### ✅ Pros:
- Kubernetes-native
- Easy to use
- Templating for different environments
- Can include service + annotations

### Implementation:

```yaml
# helm-chart/grafana-pls/templates/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ .Values.service.name }}
  namespace: {{ .Values.namespace }}
  annotations:
    service.beta.kubernetes.io/azure-load-balancer-internal: "true"
    {{- if .Values.pls.enabled }}
    service.beta.kubernetes.io/azure-pls-create: "true"
    service.beta.kubernetes.io/azure-pls-name: {{ .Values.pls.name }}
    service.beta.kubernetes.io/azure-pls-ip-configuration-subnet: {{ .Values.pls.subnet }}
    {{- end }}
  labels:
    app: {{ .Values.service.name }}
    chart: {{ .Chart.Name }}
spec:
  type: LoadBalancer
  {{- with .Values.service.loadBalancerIP }}
  loadBalancerIP: {{ . }}
  {{- end }}
  selector:
    {{- toYaml .Values.service.selector | nindent 4 }}
  ports:
    - name: web
      port: {{ .Values.service.port }}
      targetPort: {{ .Values.service.targetPort }}
```

```yaml
# helm-chart/grafana-pls/values.yaml
namespace: grafana-test

service:
  name: grafana-internal
  type: LoadBalancer
  port: 3000
  targetPort: 3000
  loadBalancerIP: "10.224.0.28"  # Optional
  selector:
    app: grafana

pls:
  enabled: true
  name: pls-grafana-helm
  subnet: aks-subnet
```

**Deploy**:
```bash
helm install grafana-pls ./helm-chart/grafana-pls \
  --namespace grafana-test \
  --values values.yaml

# If deleted
helm upgrade --install grafana-pls ./helm-chart/grafana-pls
```

---

## Strategy 3: GitOps (ArgoCD/Flux) ⭐⭐⭐⭐⭐

**Best for**: Automated self-healing environments

### ✅ Pros:
- **Automatic reconciliation** - Detects and fixes deletions
- Git is source of truth
- Continuous sync
- Audit trail
- Self-healing

### Implementation:

```yaml
# argocd-apps/grafana-pls.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: grafana-pls
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/drivenets/dap-devops
    targetRevision: main
    path: manifests/grafana-pls
  destination:
    server: https://kubernetes.default.svc
    namespace: grafana-test
  syncPolicy:
    automated:
      prune: false
      selfHeal: true  # ← Auto-recreates deleted resources!
    syncOptions:
      - CreateNamespace=true
```

**What Happens**:
```
1. Service gets deleted
      ↓
2. ArgoCD detects drift (every 3 minutes)
      ↓
3. ArgoCD automatically recreates service
      ↓
4. Service back up in < 5 minutes!
```

### Setup:

```bash
# Already have ArgoCD in your repo
kubectl apply -f argocd-apps/grafana-pls.yaml

# ArgoCD will:
# - Monitor Git repository
# - Sync changes automatically
# - Self-heal if resources are deleted
```

---

## Strategy 4: Backup & Documentation ⭐⭐⭐

**Best for**: Small setups, testing environments

### ✅ Pros:
- Simple
- No additional tools
- Clear documentation

### ❌ Cons:
- Manual recovery
- Human error prone
- Slower recovery

### Implementation:

#### **Backup Current Configuration**:

```bash
# Save service configuration
kubectl get svc grafana -n grafana-test -o yaml > backup/grafana-service.yaml

# Save PLS details
az network private-link-service show \
  --resource-group MC_rg-observability-aks_aks-observability_westus2 \
  --name pls-acf86472795934f6ba3f94ba5c3e567d \
  --output yaml > backup/grafana-pls.yaml

# Document frontend IP
kubectl get svc grafana -n grafana-test -o jsonpath='{.status.loadBalancer.ingress[0].ip}' > backup/lb-ip.txt
```

#### **Recovery Playbook**:

Create a runbook: `docs/grafana-pls-recovery.md`

```markdown
# Grafana PLS Recovery Procedure

## If Service is Deleted:

### Step 1: Recreate Service
kubectl apply -f backup/grafana-service.yaml

### Step 2: Wait for Load Balancer
kubectl wait --for=jsonpath='{.status.loadBalancer.ingress}' \
  service/grafana -n grafana-test --timeout=300s

### Step 3: Get New Frontend IP Name
# See frontend IP configuration name
az network lb frontend-ip list \
  --resource-group MC_rg-observability-aks_aks-observability_westus2 \
  --lb-name kubernetes-internal

### Step 4: Recreate PLS
az network private-link-service create \
  --resource-group MC_rg-observability-aks_aks-observability_westus2 \
  --name pls-grafana-observability \
  --vnet-name aks-vnet-38705521 \
  --subnet aks-subnet \
  --lb-frontend-ip-configs <NEW_FRONTEND_IP_ID> \
  --location westus2

### Step 5: Update Consumers
# Share new PLS alias with all consumers
```

---

## Strategy 5: Resource Protection ⭐⭐

**Best for**: Prevention (use with other strategies)

### ✅ Pros:
- Prevents accidental deletion
- Works with any strategy
- Simple to implement

### Implementation:

#### **A. Kubernetes Finalizers**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: grafana
  namespace: grafana-test
  annotations:
    service.beta.kubernetes.io/azure-load-balancer-internal: "true"
  finalizers:
    - kubernetes.io/pvc-protection  # Prevents quick deletion
  labels:
    critical: "true"
    protected: "true"
```

#### **B. RBAC Restrictions**

```yaml
# Prevent developers from deleting the service
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: grafana-viewer
  namespace: grafana-test
rules:
  - apiGroups: [""]
    resources: ["services"]
    resourceNames: ["grafana"]
    verbs: ["get", "list"]  # No "delete"!
```

#### **C. Azure Resource Locks**

```bash
# Lock the node resource group
az lock create \
  --name "prevent-deletion" \
  --resource-group MC_rg-observability-aks_aks-observability_westus2 \
  --lock-type CanNotDelete \
  --notes "Contains critical Private Link Services"
```

**Note**: This prevents ALL deletions in the resource group, including AKS operations!

#### **D. Admission Webhooks**

```yaml
# ValidatingWebhookConfiguration
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingWebhookConfiguration
metadata:
  name: protect-critical-services
webhooks:
  - name: validate.services.grafana
    rules:
      - operations: ["DELETE"]
        apiGroups: [""]
        apiVersions: ["v1"]
        resources: ["services"]
    clientConfig:
      service:
        name: webhook-service
        namespace: default
        path: "/validate"
    admissionReviewVersions: ["v1"]
    sideEffects: None
```

---

## Recommended Approach: Combination Strategy

### **For Production** (Best Practice):

```
1. GitOps (ArgoCD) ← Primary (auto-healing)
      +
2. Terraform ← Infrastructure layer
      +
3. Resource Protection ← Prevention
      +
4. Backup & Documentation ← Last resort
```

### **Implementation**:

```
┌──────────────────────────────────────────────┐
│ Git Repository (Source of Truth)              │
│ - manifests/grafana-pls/service.yaml         │
│ - terraform/grafana-pls/                     │
│ - docs/recovery-procedures.md               │
└────────────┬─────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────┐
│ ArgoCD (Continuous Sync)                     │
│ - Monitors Git                               │
│ - Auto-applies changes                       │
│ - Self-heals deletions                       │
└────────────┬─────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────┐
│ Kubernetes Cluster                           │
│ - Service with Internal LB                   │
│ - Resource protections enabled               │
└────────────┬─────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────┐
│ Azure (Managed by Terraform)                 │
│ - Private Link Service                       │
│ - Load Balancer                              │
└──────────────────────────────────────────────┘
```

---

## Quick Start: Choose Your Strategy

### **For Immediate Protection (Today)**:

```bash
# 1. Backup configuration
kubectl get svc grafana -n grafana-test -o yaml > grafana-service-backup.yaml

# 2. Add label for tracking
kubectl label svc grafana -n grafana-test critical=true protected=true

# 3. Document the setup
# Create docs/grafana-pls-recovery.md with recovery steps
```

### **For Long-term (This Week)**:

1. **Implement GitOps**:
   ```bash
   # You already have ArgoCD!
   cd /Users/avieru/01_Work/00_GitHub/drivenets/dap-devops
   
   # Create manifest
   mkdir -p manifests/grafana-pls
   kubectl get svc grafana -n grafana-test -o yaml > manifests/grafana-pls/service.yaml
   
   # Create ArgoCD app
   kubectl apply -f argocd-apps/grafana-pls.yaml
   ```

2. **Add Terraform** (optional):
   ```bash
   # Use the module created at:
   terraform-k8s-setup/modules/grafana-pls/
   ```

---

## Recovery Time Comparison

| Strategy | Detection Time | Recovery Time | Manual Steps |
|----------|----------------|---------------|--------------|
| **GitOps** | 3 minutes | 2-5 minutes | 0 (automatic) |
| **Terraform** | Manual | 5-10 minutes | 1 command |
| **Helm** | Manual | 2-5 minutes | 1 command |
| **Backup** | Manual | 15-30 minutes | 5-10 steps |
| **Manual Recreation** | Manual | 30-60 minutes | 10+ steps |

---

## Summary: Best Practices

✅ **DO**:
1. Use GitOps for automatic healing
2. Store configuration in Git
3. Document recovery procedures
4. Add resource protections
5. Test recovery process regularly

❌ **DON'T**:
1. Rely only on manual backups
2. Give everyone delete permissions
3. Skip documentation
4. Forget to test recovery
5. Use only one strategy

---

## Next Steps

1. **Immediate** (Today):
   - [ ] Backup current configuration
   - [ ] Document PLS alias and settings
   - [ ] Add critical labels to service

2. **Short-term** (This Week):
   - [ ] Implement GitOps with ArgoCD
   - [ ] Create Terraform module
   - [ ] Set up RBAC restrictions

3. **Long-term** (This Month):
   - [ ] Test recovery procedures
   - [ ] Automate backups
   - [ ] Monitor PLS health
   - [ ] Create runbooks

---

**Your Current Setup**:
- Service: `grafana` (grafana-test namespace)
- Load Balancer IP: `10.224.0.28`
- PLS: `pls-acf86472795934f6ba3f94ba5c3e567d`
- Private Endpoint: `pe-avieru-test-grafana` (10.238.0.4)

**Recommendation**: Start with **GitOps (ArgoCD)** since you already have it installed! It provides automatic healing with minimal effort.


