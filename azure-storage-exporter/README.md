# Azure Storage Account Prometheus Exporter

A Prometheus exporter that collects storage usage metrics from Azure Storage Accounts and exposes them for monitoring and alerting.

## Features

- **Container-level metrics**: Track storage usage and blob count for each container
- **Account-level metrics**: Monitor total storage account usage
- **High performance**: Smart caching and parallel processing for fast metric collection
- **Prometheus native**: Exposes metrics in Prometheus format
- **Cloud-native**: Runs as a containerized application in Kubernetes
- **Flexible authentication**: Supports both Managed Identity and Service Principal
- **Production-ready**: Includes health checks, proper logging, and security best practices

## Performance

The exporter is optimized for large storage accounts through:
- **Smart caching**: Configurable cache TTL (default 15 minutes) to reduce Azure API calls
- **Parallel processing**: Multiple containers processed simultaneously (default 10 workers)
- **Background refresh**: Stale cache served while fresh data fetched asynchronously
- **5-10x faster**: Typical scrape time reduced from minutes to seconds for large accounts

See [PERFORMANCE_OPTIMIZATION.md](PERFORMANCE_OPTIMIZATION.md) for detailed tuning guide.

## Metrics Exposed

| Metric Name | Type | Description | Labels |
|------------|------|-------------|--------|
| `azure_storage_container_size_bytes` | Gauge | Size of each container in bytes | `storage_account`, `container_name`, `resource_group` |
| `azure_storage_account_total_size_bytes` | Gauge | Total size of the storage account | `storage_account`, `resource_group` |
| `azure_storage_container_blob_count` | Gauge | Number of blobs in each container | `storage_account`, `container_name`, `resource_group` |
| `azure_storage_exporter_scrape_duration_seconds` | Histogram | Time taken to scrape metrics | - |
| `azure_storage_exporter_scrape_errors_total` | Counter | Total number of scrape errors | - |
| `azure_storage_exporter_last_scrape_timestamp` | Gauge | Timestamp of last successful scrape | - |
| `azure_storage_exporter_cache_hits_total` | Counter | Total number of cache hits | - |
| `azure_storage_exporter_cache_misses_total` | Counter | Total number of cache misses | - |
| `azure_storage_exporter_cache_age_seconds` | Gauge | Age of cached data in seconds | - |

## Prerequisites

- Azure subscription with access to Storage Account
- Azure Container Registry (ACR) or other container registry
- Kubernetes cluster (AKS recommended)
- Prometheus or Prometheus Operator installed in the cluster
- Azure CLI installed locally (for deployment)
- Docker installed locally (for building)

## Quick Start

### 1. Build and Push the Docker Image

The build script uses Docker buildx to create multi-platform images (linux/amd64) that work on AKS nodes, regardless of whether you're building on macOS (ARM64) or Linux (AMD64).

```bash
# Set your ACR name
export ACR_NAME="myregistry"

# Optional: Set a specific version tag
export IMAGE_TAG="v1.0.0"

# Build and push
cd azure-storage-exporter
chmod +x build-and-push.sh
./build-and-push.sh
```

**Note**: The script automatically:
- Creates a buildx builder for cross-platform builds
- Builds the image for linux/amd64 architecture (AKS default)
- Pushes directly to ACR without storing locally

### 2. Configure Azure Credentials

You have two options for authentication:

#### Option A: Managed Identity (Recommended for AKS)

1. Enable Workload Identity on your AKS cluster
2. Create a managed identity with Storage Blob Data Reader role
3. Update the ServiceAccount annotation in `k8s/01-serviceaccount.yaml`

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: azure-storage-exporter
  namespace: monitoring
  annotations:
    azure.workload.identity/client-id: "<your-managed-identity-client-id>"
```

#### Option B: Service Principal

```bash
# Create a service principal
az ad sp create-for-rbac --name azure-storage-exporter-sp

# Assign Storage Blob Data Reader role
az role assignment create \
  --assignee <client-id> \
  --role "Storage Blob Data Reader" \
  --scope /subscriptions/<subscription-id>/resourceGroups/<resource-group>/providers/Microsoft.Storage/storageAccounts/<storage-account>

# Set environment variables
export AZURE_TENANT_ID="<your-tenant-id>"
export AZURE_CLIENT_ID="<your-client-id>"
export AZURE_CLIENT_SECRET="<your-client-secret>"
```

### 3. Deploy to Kubernetes

```bash
# Set required environment variables
export AZURE_SUBSCRIPTION_ID="<your-subscription-id>"
export AZURE_STORAGE_ACCOUNT_NAME="<your-storage-account-name>"
export AZURE_RESOURCE_GROUP_NAME="<your-resource-group-name>"

# Optional: Set Service Principal credentials (if not using Managed Identity)
export AZURE_TENANT_ID="<your-tenant-id>"
export AZURE_CLIENT_ID="<your-client-id>"
export AZURE_CLIENT_SECRET="<your-client-secret>"

# Update the image name in k8s/03-deployment.yaml
# Change: <your-acr-name>.azurecr.io/azure-storage-exporter:latest
# To: myregistry.azurecr.io/azure-storage-exporter:latest

# Deploy
chmod +x deploy.sh
./deploy.sh
```

### 4. Verify Deployment

```bash
# Check pod status
kubectl get pods -n monitoring -l app=azure-storage-exporter

# View logs
kubectl logs -n monitoring -l app=azure-storage-exporter -f

# Test metrics endpoint
kubectl port-forward -n monitoring svc/azure-storage-exporter 9358:9358

# In another terminal
curl http://localhost:9358/metrics
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AZURE_SUBSCRIPTION_ID` | Yes | - | Azure subscription ID |
| `AZURE_STORAGE_ACCOUNT_NAME` | Yes | - | Storage account name to monitor |
| `AZURE_RESOURCE_GROUP_NAME` | Yes | - | Resource group containing the storage account |
| `AZURE_TENANT_ID` | No | - | Azure AD tenant ID (for Service Principal) |
| `AZURE_CLIENT_ID` | No | - | Service Principal client ID |
| `AZURE_CLIENT_SECRET` | No | - | Service Principal client secret |
| `EXPORTER_PORT` | No | 9358 | Port to expose metrics on |
| `SCRAPE_INTERVAL_SECONDS` | No | 300 | How often to collect metrics (not used in current implementation) |
| `LOG_LEVEL` | No | INFO | Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL |

### Kubernetes Resources

The deployment includes:

- **Namespace**: `monitoring`
- **ServiceAccount**: `azure-storage-exporter`
- **Secret**: `azure-storage-exporter-credentials`
- **Deployment**: Single replica (can be scaled if needed)
- **Service**: ClusterIP on port 9358
- **ServiceMonitor**: For Prometheus Operator
- **PodMonitor**: Alternative to ServiceMonitor

## Prometheus Configuration

### Using Prometheus Operator

If you have Prometheus Operator installed, the ServiceMonitor will be automatically discovered:

```bash
kubectl apply -f k8s/05-servicemonitor.yaml
```

### Manual Prometheus Configuration

Add this to your Prometheus configuration:

```yaml
scrape_configs:
  - job_name: 'azure-storage-exporter'
    static_configs:
      - targets: ['azure-storage-exporter.monitoring.svc.cluster.local:9358']
    scrape_interval: 60s
    scrape_timeout: 30s
```

## Example Prometheus Queries

### Container Storage Usage

```promql
# Storage usage by container
azure_storage_container_size_bytes{storage_account="mystorageaccount"}

# Storage usage in GB
azure_storage_container_size_bytes / 1024 / 1024 / 1024

# Top 5 largest containers
topk(5, azure_storage_container_size_bytes)
```

### Account-Level Metrics

```promql
# Total storage account usage
azure_storage_account_total_size_bytes

# Total storage account usage in GB
azure_storage_account_total_size_bytes / 1024 / 1024 / 1024
```

### Blob Count Metrics

```promql
# Number of blobs per container
azure_storage_container_blob_count

# Total blobs across all containers
sum(azure_storage_container_blob_count) by (storage_account)
```

### Exporter Health Metrics

```promql
# Scrape duration
azure_storage_exporter_scrape_duration_seconds

# Scrape errors
rate(azure_storage_exporter_scrape_errors_total[5m])
```

## Grafana Dashboard

A pre-built Grafana dashboard is included: `grafana-dashboard.json`

**Features**:
- 📊 Storage overview with capacity and waste metrics
- 📈 Time-series graphs showing storage trends
- 🥧 Pie chart of top 10 containers by size
- 📋 Detailed container table with waste percentage
- ⚡ Exporter performance metrics (cache hit rate, scrape duration)
- 🎨 Color-coded waste detection (green/yellow/orange/red)

**Import Instructions**:
1. Open Grafana → **Dashboards** → **Import**
2. Upload `grafana-dashboard.json`
3. Select your Prometheus/VictoriaMetrics datasource
4. Dashboard is ready to use!

See [DASHBOARD_GUIDE.md](DASHBOARD_GUIDE.md) for detailed documentation.

## Alerting Rules

Example Prometheus alerting rules:

```yaml
groups:
  - name: azure_storage_alerts
    interval: 5m
    rules:
      - alert: StorageAccountNearCapacity
        expr: azure_storage_account_total_size_bytes / 1024 / 1024 / 1024 > 4500
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Storage account {{ $labels.storage_account }} is near capacity"
          description: "Storage usage is {{ $value }}GB (threshold: 4500GB)"

      - alert: ContainerGrowthAnomaly
        expr: |
          (
            azure_storage_container_size_bytes - 
            azure_storage_container_size_bytes offset 1h
          ) / azure_storage_container_size_bytes offset 1h > 0.5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Container {{ $labels.container_name }} growing rapidly"
          description: "Container size increased by {{ $value | humanizePercentage }} in 1 hour"

      - alert: StorageExporterDown
        expr: up{job="azure-storage-exporter"} == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Azure Storage Exporter is down"
          description: "The exporter has been unreachable for more than 5 minutes"

      - alert: StorageExporterErrors
        expr: rate(azure_storage_exporter_scrape_errors_total[5m]) > 0
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Azure Storage Exporter experiencing errors"
          description: "Error rate: {{ $value | humanize }} errors/sec"
```

## Troubleshooting

### Check Pod Status

```bash
kubectl get pods -n monitoring -l app=azure-storage-exporter
kubectl describe pod -n monitoring -l app=azure-storage-exporter
```

### View Logs

```bash
# Follow logs
kubectl logs -n monitoring -l app=azure-storage-exporter -f

# Previous logs (if pod restarted)
kubectl logs -n monitoring -l app=azure-storage-exporter --previous
```

### Test Metrics Endpoint

```bash
kubectl port-forward -n monitoring svc/azure-storage-exporter 9358:9358
curl http://localhost:9358/metrics
```

### Common Issues

#### Authentication Errors

- **Managed Identity**: Ensure workload identity is enabled and the identity has proper RBAC roles
- **Service Principal**: Verify credentials are correct and have the required permissions

#### Permission Errors

Grant the required role to your identity:

```bash
# For Managed Identity
az role assignment create \
  --assignee <managed-identity-principal-id> \
  --role "Storage Blob Data Reader" \
  --scope /subscriptions/<subscription-id>/resourceGroups/<resource-group>/providers/Microsoft.Storage/storageAccounts/<storage-account>

# For Service Principal
az role assignment create \
  --assignee <service-principal-client-id> \
  --role "Storage Blob Data Reader" \
  --scope /subscriptions/<subscription-id>/resourceGroups/<resource-group>/providers/Microsoft.Storage/storageAccounts/<storage-account>
```

#### Metrics Not Appearing in Prometheus

1. Check ServiceMonitor is created: `kubectl get servicemonitor -n monitoring`
2. Verify Prometheus is scraping: Check Prometheus targets page
3. Check network policies aren't blocking traffic
4. Verify the exporter is exposing metrics: `curl http://localhost:9358/metrics`

#### "exec format error" in Kubernetes

This error occurs when there's an architecture mismatch between the built image and the Kubernetes node architecture.

**Cause**: Image built on ARM64 (Apple Silicon Mac) but deployed to AMD64 (AKS nodes)

**Solution**: The build script now uses Docker buildx to automatically build for the correct architecture (linux/amd64). Simply rebuild and push:

```bash
# Rebuild with the updated script
ACR_NAME=myregistry IMAGE_TAG=v1.0.1 ./build-and-push.sh

# Update the deployment to use the new tag
kubectl set image deployment/azure-storage-exporter \
  azure-storage-exporter=myregistry.azurecr.io/sre-images/azure-storage-exporter:v1.0.1 \
  -n monitoring

# Or redeploy
kubectl rollout restart deployment/azure-storage-exporter -n monitoring
```

**Verify the fix**:
```bash
# Check the image architecture
docker buildx imagetools inspect myregistry.azurecr.io/sre-images/azure-storage-exporter:latest

# Should show: linux/amd64
```

### Adjusting Log Level

To change the log level for debugging or reducing verbosity:

```bash
# Update the deployment with a new log level
kubectl set env deployment/azure-storage-exporter LOG_LEVEL=DEBUG -n monitoring

# Or edit the deployment directly
kubectl edit deployment azure-storage-exporter -n monitoring
# Change the LOG_LEVEL value under spec.template.spec.containers[0].env

# Verify the change
kubectl get pods -n monitoring -l app=azure-storage-exporter
kubectl logs -n monitoring -l app=azure-storage-exporter -f
```

**Available log levels**:
- `DEBUG`: Detailed diagnostic information (includes all blob-level details)
- `INFO`: General informational messages (default, recommended)
- `WARNING`: Warning messages only - **NOT RECOMMENDED** as it hides normal operation logs
- `ERROR`: Error messages for serious problems only
- `CRITICAL`: Critical messages for very serious errors only

**Important**: Using `WARNING`, `ERROR`, or `CRITICAL` log levels will suppress normal operational logs, making it difficult to troubleshoot issues. These levels should only be used in production environments where you only want to see problems. For troubleshooting, always use `INFO` or `DEBUG`.

### Pod Shows 0 CPU/Memory or No Metrics

If the exporter pod shows 0 CPU/memory usage or metrics aren't being collected:

1. **Check if pod is running**:
```bash
kubectl get pods -n dap-o11y -l app=azure-storage-exporter
kubectl describe pod -n dap-o11y -l app=azure-storage-exporter
```

2. **Check logs for errors** (errors always show regardless of log level):
```bash
# View logs
kubectl logs -n dap-o11y -l app=azure-storage-exporter

# If LOG_LEVEL is WARNING and you see NO logs, the app might not have started
# Change to INFO to see startup messages
kubectl set env deployment/azure-storage-exporter LOG_LEVEL=INFO -n dap-o11y
```

3. **Test the metrics endpoint directly**:
```bash
# Port forward to the pod
kubectl port-forward -n dap-o11y svc/azure-storage-exporter 9358:9358

# In another terminal, check if metrics are being exposed
curl http://localhost:9358/metrics | grep azure_storage

# Check for error metrics
curl http://localhost:9358/metrics | grep scrape_errors
```

4. **Verify Azure credentials are correct**:
```bash
# Check if secret exists and has the right keys
kubectl get secret azure-storage-exporter-credentials -n dap-o11y -o yaml

# Exec into the pod and test Azure connectivity
kubectl exec -it -n dap-o11y deployment/azure-storage-exporter -- sh
# (if shell works, check env vars are set)
env | grep AZURE
```

5. **Common causes of 0 CPU/Memory**:
   - Pod is in CrashLoopBackOff (check with `kubectl describe pod`)
   - Authentication failure (check logs for Azure auth errors)
   - Missing required environment variables
   - Network policies blocking Azure API access

## Security Considerations

- **Least Privilege**: Use Managed Identity when possible
- **RBAC**: Grant only "Storage Blob Data Reader" role
- **Network Security**: Use network policies to restrict access
- **Secret Management**: Consider using Azure Key Vault for secrets
- **Security Context**: Pod runs as non-root user (UID 1000)
- **Read-Only Filesystem**: Container uses read-only root filesystem

## Performance Considerations

- **Large Storage Accounts**: Scraping may take time for accounts with many containers
- **Rate Limiting**: Azure APIs have rate limits; adjust scrape interval accordingly
- **Resource Limits**: Adjust memory/CPU limits based on your storage account size
- **Caching**: Consider implementing caching for very large accounts

## Development

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export AZURE_SUBSCRIPTION_ID="<your-subscription-id>"
export AZURE_STORAGE_ACCOUNT_NAME="<your-storage-account>"
export AZURE_RESOURCE_GROUP_NAME="<your-resource-group>"

# Run locally
python3 azure_storage_exporter.py
```

### Testing

```bash
# Test metrics endpoint
curl http://localhost:9358/metrics

# Test specific storage account
export AZURE_STORAGE_ACCOUNT_NAME="teststorage"
python3 azure_storage_exporter.py
```

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Follow the existing code style (PEP 8 for Python)
2. Add tests for new features
3. Update documentation as needed
4. Use meaningful commit messages

## License

This project is licensed under the MIT License.

## Support

For issues and questions:
- Create an issue in the repository
- Contact the DevOps team

## Roadmap

Future enhancements:
- [ ] Support for multiple storage accounts
- [ ] Additional metrics (transaction counts, availability, etc.)
- [ ] Caching mechanism for large accounts
- [ ] Helm chart for easier deployment
- [ ] Support for other storage types (File Shares, Tables, Queues)
- [ ] Cost metrics integration
- [ ] Historical data tracking



