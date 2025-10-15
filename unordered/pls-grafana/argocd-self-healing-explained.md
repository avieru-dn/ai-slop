# ArgoCD Self-Healing Explained

## How It Works

### **The Self-Healing Loop**

```
┌─────────────────────────────────────────────────────────────┐
│                    ArgoCD Reconciliation Loop                │
└─────────────────────────────────────────────────────────────┘

Step 1: Read Desired State (from Git)
   ├── Clone repository
   ├── Read YAML files
   └── Build desired state model

Step 2: Read Actual State (from Kubernetes)
   ├── Query Kubernetes API
   ├── Get all resources in namespace
   └── Build actual state model

Step 3: Compare States
   ├── Desired: Service "grafana" should exist
   ├── Actual: Service "grafana" does NOT exist
   └── Result: DRIFT DETECTED! 🚨

Step 4: Self-Heal Decision
   ├── Is selfHeal enabled? → YES ✓
   ├── Is resource in Git? → YES ✓
   ├── Is resource missing in cluster? → YES ✓
   └── Action: RECREATE IT! 🔧

Step 5: Apply Correction
   └── kubectl apply -f manifests/grafana-pls/service.yaml

Step 6: Verify
   ├── Wait for resource creation
   ├── Check resource status
   └── Mark as "Synced" ✅

Step 7: Wait 3 Minutes
   └── Repeat from Step 1
```

---

## **Configuration Parameters**

### **selfHeal: true**

```yaml
syncPolicy:
  automated:
    selfHeal: true  # Enable automatic healing
```

**What it does:**
- ✅ Detects deleted resources
- ✅ Recreates them automatically
- ✅ Fixes modified resources (reverts to Git)
- ✅ Ensures cluster matches Git

**What it does NOT do:**
- ❌ Delete resources not in Git (unless `prune: true`)
- ❌ Modify resources not managed by ArgoCD
- ❌ Interfere with resources in other namespaces

---

### **prune: false** (Important!)

```yaml
syncPolicy:
  automated:
    prune: false  # Don't auto-delete extra resources
```

**Why false?**
- Prevents accidental deletion of resources
- Safe for production
- You manually delete when needed

**If true:**
- ArgoCD deletes resources NOT in Git
- Can be dangerous if misconfigured
- Use only in dev environments

---

## **Reconciliation Frequency**

### **Default: Every 3 Minutes**

```yaml
# ArgoCD ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  # Default reconciliation interval
  timeout.reconciliation: 180s  # 3 minutes
```

### **Can Be Customized:**

```yaml
# Per-application override
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: grafana-pls
spec:
  syncPolicy:
    automated:
      selfHeal: true
    syncOptions:
      - RespectIgnoreDifferences=true
  # Override reconciliation interval
  info:
    - name: 'Reconciliation Interval'
      value: '60s'  # Check every 1 minute
```

---

## **Real-World Example: Your Grafana Service**

### **Before Self-Healing:**

```bash
# Service gets deleted
kubectl delete svc grafana -n grafana-test

# Manual recovery required:
# 1. Notice it's gone (human detection time: varies)
# 2. Find backup configuration
# 3. Apply it: kubectl apply -f backup.yaml
# 4. Wait for load balancer
# 5. Manually recreate PLS
# 6. Update consumers

Total time: 30-60 minutes + human intervention
```

### **With Self-Healing:**

```bash
# Service gets deleted
kubectl delete svc grafana -n grafana-test

# ArgoCD automatically:
# 1. Detects deletion (max 3 minutes)
# 2. Applies configuration from Git
# 3. Service recreated
# 4. Load balancer recreated

Total time: 3-5 minutes, zero human intervention ✅
```

---

## **Self-Healing Scenarios**

### **Scenario 1: Resource Deleted**

```yaml
# Git: Service should exist
apiVersion: v1
kind: Service
metadata:
  name: grafana

# Cluster: Service is missing ❌
```

**ArgoCD Action**: `kubectl apply -f service.yaml` (recreates it)

---

### **Scenario 2: Resource Modified**

```yaml
# Git: Service should have this config
spec:
  type: LoadBalancer
  ports:
    - port: 3000

# Cluster: Someone changed it ❌
spec:
  type: LoadBalancer
  ports:
    - port: 8080  # Wrong!
```

**ArgoCD Action**: Reverts to Git configuration (port 3000)

---

### **Scenario 3: Resource Scaled**

```yaml
# Git: Deployment should have 2 replicas
spec:
  replicas: 2

# Cluster: HPA scaled it to 5 ❌
spec:
  replicas: 5  # HPA did this
```

**ArgoCD Action**: 
- By default: Reverts to 2 (breaks HPA!)
- **Solution**: Use `ignoreDifferences` for HPA-managed fields

```yaml
spec:
  ignoreDifferences:
    - group: apps
      kind: Deployment
      jsonPointers:
        - /spec/replicas  # Ignore replica count
```

---

## **Advanced: Sync Waves**

Control the order of resource creation:

```yaml
# 1. Create service first
apiVersion: v1
kind: Service
metadata:
  name: grafana
  annotations:
    argocd.argoproj.io/sync-wave: "1"  # Create first
spec:
  type: LoadBalancer

---
# 2. Then create ingress
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: grafana-ingress
  annotations:
    argocd.argoproj.io/sync-wave: "2"  # Create after service
```

**Benefits**:
- Ensures proper order during self-heal
- Service created before dependent resources
- Prevents temporary errors

---

## **Monitoring Self-Healing**

### **ArgoCD UI**

1. Open ArgoCD UI
2. Go to your application: `grafana-pls`
3. Watch the sync status

**Indicators:**
- 🟢 **Synced**: Everything matches Git
- 🟡 **OutOfSync**: Drift detected, healing in progress
- 🔴 **Failed**: Healing failed (check logs)

### **CLI Monitoring**

```bash
# Watch application status
argocd app get grafana-pls --watch

# See sync history
argocd app history grafana-pls

# View recent events
kubectl get events -n grafana-test --sort-by='.lastTimestamp'
```

### **Metrics**

ArgoCD exposes Prometheus metrics:

```promql
# Number of self-heal operations
argocd_app_reconcile_count{dest_namespace="grafana-test",health_status="Healthy"}

# Time to heal
argocd_app_sync_duration_seconds{application="grafana-pls"}
```

---

## **Best Practices for Self-Healing**

### **1. Start with selfHeal: false**

Test first, then enable:

```yaml
syncPolicy:
  automated:
    selfHeal: false  # Test manually first
    prune: false
```

Once confident:

```yaml
syncPolicy:
  automated:
    selfHeal: true   # Enable auto-healing
    prune: false     # Keep this false!
```

---

### **2. Use Sync Windows** (Optional)

Prevent healing during maintenance:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: grafana-pls
spec:
  syncPolicy:
    syncWindows:
      - kind: deny
        schedule: '0 2 * * *'  # No sync at 2 AM
        duration: 1h
        applications:
          - grafana-pls
```

---

### **3. Add Health Checks**

Tell ArgoCD how to check if resources are healthy:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: grafana
  annotations:
    argocd.argoproj.io/health-check: |
      hs = {}
      if obj.status.loadBalancer.ingress ~= nil then
        hs.status = "Healthy"
        hs.message = "Load balancer is ready"
      else
        hs.status = "Progressing"
        hs.message = "Waiting for load balancer IP"
      end
      return hs
```

---

### **4. Use Notifications**

Get alerted when self-healing occurs:

```yaml
# argocd-notifications ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  trigger.on-deployed: |
    - when: app.status.operationState.phase == 'Succeeded'
      send: [app-deployed]
  
  trigger.on-health-degraded: |
    - when: app.status.health.status == 'Degraded'
      send: [app-health-degraded]
  
  template.app-deployed: |
    message: |
      Application {{.app.metadata.name}} has been synced.
      Self-healing may have occurred.
```

---

## **Testing Self-Healing**

### **Test 1: Delete Service**

```bash
# 1. Delete the service
kubectl delete svc grafana -n grafana-test

# 2. Watch ArgoCD
argocd app get grafana-pls --watch

# Expected:
# - Status changes to "OutOfSync"
# - After max 3 minutes, auto-sync starts
# - Status changes to "Syncing"
# - Service recreated
# - Status changes to "Synced"

# 3. Verify service is back
kubectl get svc grafana -n grafana-test
```

---

### **Test 2: Modify Service**

```bash
# 1. Change service port
kubectl patch svc grafana -n grafana-test -p '{"spec":{"ports":[{"port":8080,"targetPort":3000}]}}'

# 2. Watch ArgoCD detect and fix it
argocd app get grafana-pls --watch

# Expected:
# - ArgoCD detects drift
# - Reverts to port 3000 from Git
```

---

### **Test 3: Force Sync**

```bash
# Manually trigger sync (doesn't wait 3 minutes)
argocd app sync grafana-pls

# With options
argocd app sync grafana-pls --force --prune=false
```

---

## **Troubleshooting Self-Healing**

### **Issue: Self-Healing Not Working**

**Check 1: Is selfHeal enabled?**
```bash
argocd app get grafana-pls -o yaml | grep selfHeal
# Should show: selfHeal: true
```

**Check 2: Is app auto-sync enabled?**
```bash
argocd app get grafana-pls -o yaml | grep automated
# Should show automated section
```

**Check 3: Are there sync errors?**
```bash
argocd app get grafana-pls
# Look for error messages in "Last Sync Result"
```

---

### **Issue: Self-Healing Too Aggressive**

If ArgoCD keeps reverting your changes:

**Solution 1: Add to Git**
```bash
# If you need the change permanently
git add manifests/grafana-pls/service.yaml
git commit -m "Update service configuration"
git push
```

**Solution 2: Ignore specific fields**
```yaml
spec:
  ignoreDifferences:
    - group: ""
      kind: Service
      jsonPointers:
        - /spec/clusterIP  # Ignore auto-assigned IPs
```

---

## **Summary: Self-Healing Process**

```
┌─────────────────────────────────────────────────────────┐
│ SELF-HEALING TIMELINE                                    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ T+0:00   Resource deleted manually                      │
│          └── Service: grafana ❌                        │
│                                                          │
│ T+0:00   Cluster state changes                          │
│          └── Load Balancer removed                      │
│          └── PLS becomes broken                         │
│                                                          │
│ T+3:00   ArgoCD reconciliation runs                     │
│          └── Reads Git: expects grafana service         │
│          └── Reads Cluster: service missing             │
│          └── DRIFT DETECTED! 🚨                         │
│                                                          │
│ T+3:01   Self-healing kicks in                          │
│          └── kubectl apply -f service.yaml              │
│                                                          │
│ T+3:02   Service created ✅                             │
│          └── Kubernetes provisions Load Balancer        │
│                                                          │
│ T+3:04   Load Balancer ready                            │
│          └── IP assigned: 10.224.0.28                   │
│                                                          │
│ T+3:05   System restored ✅                             │
│          └── Everything back to normal                  │
│          └── Total downtime: ~5 minutes                 │
│          └── Human intervention: ZERO!                  │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## **Your Next Steps**

To enable self-healing for your Grafana PLS:

```bash
# 1. Save current service to Git
kubectl get svc grafana -n grafana-test -o yaml > manifests/grafana-pls/service.yaml

# 2. Clean up auto-generated fields
# Remove: resourceVersion, uid, creationTimestamp, status

# 3. Commit to Git
git add manifests/grafana-pls/
git commit -m "Add Grafana service for ArgoCD management"
git push

# 4. Create ArgoCD Application
kubectl apply -f - <<EOF
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
      selfHeal: true  # ← Magic happens here!
      prune: false
    syncOptions:
      - CreateNamespace=true
EOF

# 5. Watch it work
argocd app get grafana-pls --watch

# 6. Test it!
kubectl delete svc grafana -n grafana-test
# Wait 3 minutes... service comes back automatically! ✨
```

**That's self-healing!** 🎉


