# Kubernetes Standards and Best Practices

## Manifest Structure

### Required Fields
Every manifest must include:
- `apiVersion`
- `kind`
- `metadata.name`
- `metadata.namespace` (except for cluster-scoped resources)
- `metadata.labels`

### Recommended Labels
```yaml
metadata:
  labels:
    app.kubernetes.io/name: myapp
    app.kubernetes.io/instance: myapp-abcxzy
    app.kubernetes.io/version: "1.0.0"
    app.kubernetes.io/component: database
    app.kubernetes.io/part-of: myapp-system
    app.kubernetes.io/managed-by: helm
    environment: production
    team: platform
```

## Pod Configuration

### Resource Management
Always specify resources:
```yaml
resources:
  requests:
    memory: "64Mi"
    cpu: "250m"
  limits:
    memory: "128Mi"
    cpu: "500m"
```

### Health Checks
Implement both probes:
```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 3
```

### Security Context
```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
  capabilities:
    drop:
      - ALL
```

## Deployment Best Practices

### Deployment Strategy
```yaml
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  
  template:
    spec:
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchExpressions:
                    - key: app
                      operator: In
                      values:
                        - myapp
                topologyKey: kubernetes.io/hostname
```

### Environment Variables
```yaml
env:
  # Direct values for non-sensitive data
  - name: LOG_LEVEL
    value: "info"
  
  # ConfigMap reference
  - name: CONFIG_FILE
    valueFrom:
      configMapKeyRef:
        name: app-config
        key: config.json
  
  # Secret reference
  - name: DATABASE_PASSWORD
    valueFrom:
      secretKeyRef:
        name: db-credentials
        key: password
  
  # Downward API
  - name: POD_NAME
    valueFrom:
      fieldRef:
        fieldPath: metadata.name
```

## ConfigMaps and Secrets

### ConfigMap Usage
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: myapp
data:
  app.properties: |
    server.port=8080
    server.name=myapp
  config.json: |
    {
      "feature": "enabled"
    }
```

### Secret Management
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
  namespace: myapp
type: Opaque
stringData:
  username: admin
  password: changeme
```

**Note:** Use external secret management (Azure Key Vault, HashiCorp Vault) in production.

## Services

### Service Types
```yaml
# ClusterIP - internal only
apiVersion: v1
kind: Service
metadata:
  name: backend-service
spec:
  type: ClusterIP
  selector:
    app: backend
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8080
---
# LoadBalancer - external access
apiVersion: v1
kind: Service
metadata:
  name: frontend-service
  annotations:
    service.beta.kubernetes.io/azure-load-balancer-internal: "true"
spec:
  type: LoadBalancer
  selector:
    app: frontend
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8080
```

## Ingress

### NGINX Ingress
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - myapp.example.com
      secretName: myapp-tls
  rules:
    - host: myapp.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend-service
                port:
                  number: 80
```

## StatefulSets

### For Stateful Applications
```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: database
spec:
  serviceName: database
  replicas: 3
  selector:
    matchLabels:
      app: database
  template:
    spec:
      containers:
        - name: database
          image: postgres:14
          volumeMounts:
            - name: data
              mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: managed-premium
        resources:
          requests:
            storage: 10Gi
```

## Persistent Volumes

### PersistentVolumeClaim
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data-pvc
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: managed-premium
  resources:
    requests:
      storage: 10Gi
```

## Network Policies

### Restrict Traffic
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-network-policy
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8080
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: database
      ports:
        - protocol: TCP
          port: 5432
```

## Autoscaling

### Horizontal Pod Autoscaler
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: app
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

### Vertical Pod Autoscaler
```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: app-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: app
  updatePolicy:
    updateMode: "Auto"
```

## RBAC

### ServiceAccount
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-sa
  namespace: myapp
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: app-role
  namespace: myapp
rules:
  - apiGroups: [""]
    resources: ["configmaps", "secrets"]
    verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: app-rolebinding
  namespace: myapp
subjects:
  - kind: ServiceAccount
    name: app-sa
roleRef:
  kind: Role
  name: app-role
  apiGroup: rbac.authorization.k8s.io
```

## Monitoring

### ServiceMonitor (Prometheus Operator)
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: app-metrics
  labels:
    release: prometheus
spec:
  selector:
    matchLabels:
      app: myapp
  endpoints:
    - port: metrics
      interval: 30s
      path: /metrics
```

## GitOps Best Practices

### Directory Structure
```
k8s/
├── base/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── kustomization.yaml
├── overlays/
│   ├── dev/
│   │   ├── kustomization.yaml
│   │   └── patches/
│   ├── staging/
│   │   ├── kustomization.yaml
│   │   └── patches/
│   └── prod/
│       ├── kustomization.yaml
│       └── patches/
```

### Kustomization
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: myapp-prod

commonLabels:
  environment: production

resources:
  - ../../base

replicas:
  - name: app
    count: 5

images:
  - name: myapp
    newTag: v1.2.3
```

## High Availability Checklist

- ✅ Multiple replicas (minimum 3 for production)
- ✅ Pod anti-affinity rules
- ✅ Resource requests and limits defined
- ✅ Liveness and readiness probes configured
- ✅ PodDisruptionBudget defined
- ✅ Horizontal Pod Autoscaler configured
- ✅ Node affinity for critical workloads
- ✅ Health checks for all services
- ✅ Monitoring and alerting in place
- ✅ Backup strategy for persistent data

