# Grafana Dashboard Guide

## Overview

The Azure Storage Exporter Dashboard provides comprehensive visualization of your Azure Storage Account metrics with focus on:
- Storage capacity and growth
- Container-level breakdown
- Waste detection (deleted blobs, snapshots, versions)
- Exporter performance and cache efficiency

## Dashboard Sections

### 1. Storage Overview
**Top Row - Key Metrics**:
- **Total Storage (Active)**: Current size of active blobs only
- **Total Storage (All Data)**: Includes active + deleted + snapshots + versions
- **Deleted Blobs Size**: How much storage is used by soft-deleted blobs
- **Wasted Storage %**: Percentage of storage used by deleted/snapshot/version data

**Storage Trend Graph**:
- Time series showing storage growth
- Color-coded by data type (Active, Deleted, Snapshots, Versions)
- Shows max and current values in legend

### 2. Container Details
**Pie Chart - Top 10 Containers**:
- Visual breakdown of which containers use most storage
- Percentage and actual size shown
- Interactive legend

**Container Table**:
- Sortable table with all containers
- Columns:
  - **Container**: Container name
  - **Active Size (GB)**: Current blob storage
  - **Deleted Size (GB)**: Soft-deleted blob storage
  - **Blob Count**: Number of active blobs
  - **Waste %**: Percentage of wasted storage (color-coded)
    - 🟢 Green: < 10%
    - 🟡 Yellow: 10-25%
    - 🟠 Orange: 25-50%
    - 🔴 Red: > 50%

### 3. Exporter Performance
**Cache Metrics**:
- **Cache Hit Rate**: Should be > 80% for good performance
- **Cache Age**: Current age of cached data (oscillates between 0 and TTL)
- **Avg Scrape Duration**: Average time to return metrics
- **Exporter Status**: UP/DOWN indicator

**Performance Graphs**:
- **Scrape Duration Percentiles**: p50, p95, p99 response times
- **Cache Hit/Miss Rate**: Visual representation of cache efficiency

## How to Import

### Method 1: Grafana UI
1. Open Grafana
2. Click **Dashboards** → **Import**
3. Click **Upload JSON file**
4. Select `grafana-dashboard.json`
5. Select your Prometheus/VictoriaMetrics datasource
6. Click **Import**

### Method 2: Via API
```bash
# Set your Grafana URL and API key
GRAFANA_URL="https://your-grafana.com"
API_KEY="your-api-key"

# Import the dashboard
curl -X POST \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d @grafana-dashboard.json \
  "${GRAFANA_URL}/api/dashboards/db"
```

### Method 3: ConfigMap in Kubernetes
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: azure-storage-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  azure-storage-exporter.json: |
    # Paste the content of grafana-dashboard.json here
```

Then configure Grafana to auto-discover dashboards from ConfigMaps.

## Dashboard Variables

### Datasource
- **Purpose**: Select which Prometheus/VictoriaMetrics datasource to use
- **Type**: Dropdown
- **Required**: Yes

### Storage Account
- **Purpose**: Filter metrics by storage account
- **Type**: Dropdown
- **Source**: Auto-populated from metrics
- **Required**: Yes

## Key Queries

### Storage Capacity
```promql
# Total active storage in GB
azure_storage_account_total_size_bytes{storage_account="$storage_account"} / 1024 / 1024 / 1024

# Total including all data types
azure_storage_account_total_size_all_bytes{storage_account="$storage_account"} / 1024 / 1024 / 1024
```

### Waste Calculation
```promql
# Percentage of wasted storage
(azure_storage_account_total_deleted_size_bytes{storage_account="$storage_account"} + 
 sum(azure_storage_container_snapshot_size_bytes{storage_account="$storage_account"}) + 
 sum(azure_storage_container_version_size_bytes{storage_account="$storage_account"})) / 
 azure_storage_account_total_size_all_bytes{storage_account="$storage_account"} * 100
```

### Cache Performance
```promql
# Cache hit rate
rate(azure_storage_exporter_cache_hits_total[5m]) /
(rate(azure_storage_exporter_cache_hits_total[5m]) + 
 rate(azure_storage_exporter_cache_misses_total[5m])) * 100
```

### Scrape Duration
```promql
# Average scrape time
rate(azure_storage_exporter_scrape_duration_seconds_sum[5m]) / 
rate(azure_storage_exporter_scrape_duration_seconds_count[5m])

# p95 scrape duration
histogram_quantile(0.95, 
  rate(azure_storage_exporter_scrape_duration_seconds_bucket[5m]))
```

## Interpreting the Dashboard

### Healthy Metrics
✅ **Cache hit rate**: > 90%
✅ **Average scrape duration**: < 2 seconds
✅ **Exporter status**: UP (green)
✅ **Cache age**: Oscillating between 0 and cache TTL
✅ **Waste %**: < 10% (green)

### Warning Signs
⚠️ **Cache hit rate**: < 80% (may need to adjust cache TTL)
⚠️ **Average scrape duration**: > 5 seconds (cache may not be working)
⚠️ **High waste %**: > 25% (consider cleanup of deleted/snapshot data)
⚠️ **Cache age stuck**: Not changing (background refresh may be failing)

### Critical Issues
🔴 **Exporter status**: DOWN (exporter pod crashed)
🔴 **Cache hit rate**: < 50% (cache misconfigured)
🔴 **Average scrape duration**: > 60 seconds (serious performance issue)
🔴 **No data**: Metrics not being collected

## Alerting Rules

Add these to Prometheus for alerts:

### High Waste Storage
```yaml
- alert: HighWasteStorage
  expr: |
    (azure_storage_account_total_deleted_size_bytes + 
     sum(azure_storage_container_snapshot_size_bytes) + 
     sum(azure_storage_container_version_size_bytes)) / 
     azure_storage_account_total_size_all_bytes * 100 > 30
  for: 1h
  labels:
    severity: warning
  annotations:
    summary: "High wasted storage detected"
    description: "Storage account {{ $labels.storage_account }} has {{ $value | humanizePercentage }} wasted storage"
```

### Storage Near Capacity
```yaml
- alert: StorageNearCapacity
  expr: |
    azure_storage_account_total_size_bytes / 1024 / 1024 / 1024 / 1024 > 4.5
  for: 30m
  labels:
    severity: warning
  annotations:
    summary: "Storage account near capacity"
    description: "Storage account {{ $labels.storage_account }} has {{ $value }}TB of data"
```

### Low Cache Hit Rate
```yaml
- alert: LowCacheHitRate
  expr: |
    rate(azure_storage_exporter_cache_hits_total[15m]) /
    (rate(azure_storage_exporter_cache_hits_total[15m]) + 
     rate(azure_storage_exporter_cache_misses_total[15m])) < 0.8
  for: 30m
  labels:
    severity: warning
  annotations:
    summary: "Azure Storage Exporter cache hit rate low"
    description: "Cache hit rate is {{ $value | humanizePercentage }} (< 80%)"
```

### Exporter Down
```yaml
- alert: AzureStorageExporterDown
  expr: up{job="azure-storage-exporter"} == 0
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Azure Storage Exporter is down"
    description: "The Azure Storage Exporter has been down for more than 5 minutes"
```

## Customization

### Change Time Range
Default: Last 6 hours

To change:
1. Click time picker (top right)
2. Select desired range or set custom range
3. Click **Save** → **Save time range changes**

### Add Custom Panels

**Example: Growth Rate Panel**
```json
{
  "expr": "deriv(azure_storage_account_total_size_bytes{storage_account=\"$storage_account\"}[1d])",
  "legendFormat": "Growth Rate (bytes/sec)"
}
```

**Example: Cost Estimation** (assuming $0.02/GB/month)
```json
{
  "expr": "azure_storage_account_total_size_all_bytes{storage_account=\"$storage_account\"} / 1024 / 1024 / 1024 * 0.02",
  "legendFormat": "Estimated Monthly Cost ($)"
}
```

### Modify Thresholds

Edit panel → Field tab → Thresholds:
- Green: Normal
- Yellow: Warning (adjust value)
- Red: Critical (adjust value)

## Best Practices

### Dashboard Usage
1. **Review daily**: Check waste % and take action if > 20%
2. **Monitor trends**: Look at storage growth over weeks/months
3. **Watch cache metrics**: Ensure cache is working efficiently
4. **Set alerts**: Don't rely on manual dashboard checks

### Performance Optimization
1. **Keep cache TTL appropriate**: 15-30 minutes for most cases
2. **Monitor cache hit rate**: Should stay > 90%
3. **Check scrape duration**: Should be < 5 seconds for cached data

### Cost Management
1. **Identify large containers**: Use pie chart to find cleanup candidates
2. **Track waste %**: Containers with high waste % are cleanup priorities
3. **Monitor growth**: Sudden spikes may indicate issues

## Troubleshooting

### No Data Showing
**Problem**: Dashboard shows "No data"

**Solutions**:
1. Check exporter is running:
   ```bash
   kubectl get pods -l app=azure-storage-exporter
   ```
2. Check metrics endpoint:
   ```bash
   kubectl port-forward svc/azure-storage-exporter 9358:9358
   curl http://localhost:9358/metrics
   ```
3. Verify Prometheus is scraping:
   ```promql
   up{job="azure-storage-exporter"}
   ```

### Dashboard Loads Slowly
**Problem**: Dashboard takes long to load

**Solutions**:
1. Reduce time range (use last 6h instead of 24h)
2. Use shorter refresh interval (1m instead of 30s)
3. Disable auto-refresh during investigation

### Metrics Look Wrong
**Problem**: Numbers don't match Azure Portal

**Solutions**:
1. Check cache age - may be showing old data
2. Wait for cache refresh (every 15 minutes by default)
3. Restart exporter pod to force immediate refresh:
   ```bash
   kubectl delete pod -l app=azure-storage-exporter
   ```

## Screenshots

### Storage Overview
Shows total capacity, waste %, and trends over time.

### Container Details
Identifies which containers use most storage and where waste occurs.

### Performance Metrics
Validates exporter is working efficiently with good cache hit rates.

## Summary

The Azure Storage Exporter Dashboard provides:
- ✅ **Real-time visibility** into storage usage
- ✅ **Cost optimization insights** via waste detection
- ✅ **Performance monitoring** of the exporter itself
- ✅ **Container-level breakdown** for targeted cleanup
- ✅ **Trend analysis** for capacity planning

Import it, set up alerts, and monitor your Azure Storage efficiently!


