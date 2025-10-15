# Speed Optimization Guide

## The Problem

**Azure blob listing is inherently slow** because:
- Azure Storage API must iterate through **every single blob** in a container
- For containers with millions of blobs, this takes **minutes per container**
- No Azure API provides pre-aggregated totals at the container level
- You **must** count every blob to get accurate metrics

## What We've Done

### 1. ✅ Caching (Biggest Impact)
```yaml
CACHE_TTL_SECONDS: "1800"  # 30 minutes
```

**Result**: After the first slow scan, subsequent Prometheus scrapes are **instant (< 1 second)**

**Trade-off**: Metrics refresh only every 30 minutes instead of real-time

### 2. ✅ Parallel Processing
```yaml
MAX_WORKERS: "20"  # Process 20 containers simultaneously
```

**Result**: If you have 20 containers, they all process at once → **20x faster**

**Trade-off**: Higher CPU/memory usage during refresh

## Realistic Expectations

### For Large Storage Accounts

If you have:
- 50 containers
- 2.5 million total blobs
- 8.5 TB total data

**Expected Performance**:

| Scenario | Time | Notes |
|----------|------|-------|
| **First scrape (cold start)** | 2-5 minutes | Must iterate ALL blobs |
| **Cached scrapes** | < 1 second | Served from memory ✅ |
| **Background refresh** | 2-5 minutes | Happens every 30 min |

### Why It Still Takes Time

**The fundamental issue**: Azure forces us to iterate through every blob to get:
- Container size
- Blob count
- Deleted blobs
- Snapshots
- Versions

There's **no faster Azure API** that gives us these numbers without iteration.

## Recommendations

### Option 1: Accept the Trade-off (Recommended)
**Use longer cache TTL** to reduce refresh frequency:

```yaml
env:
  - name: CACHE_TTL_SECONDS
    value: "3600"  # 1 hour - refresh only once per hour
  - name: MAX_WORKERS
    value: "30"    # Maximum parallelism
```

**Benefits**:
- Prometheus scrapes always succeed (< 1 second)
- Background refresh happens only once per hour
- Accurate metrics (no estimation)

**Trade-offs**:
- Metrics can be up to 1 hour old
- But for capacity planning, this is usually acceptable

### Option 2: Schedule Refreshes During Off-Hours
Run the exporter with **very long cache** and manually trigger refreshes:

```yaml
CACHE_TTL_SECONDS: "86400"  # 24 hours
```

Then restart the pod during maintenance windows to refresh data.

### Option 3: Azure Blob Inventory (Alternative Approach)

Instead of using this exporter, use **Azure Blob Inventory**:

**How it works**:
1. Azure generates daily CSV reports with all blob metadata
2. Parse the CSV files instead of calling APIs
3. Much faster (just read CSV files)

**Implementation**:
```bash
# Enable blob inventory on storage account
az storage account blob-inventory-policy create \
  --account-name $STORAGE_ACCOUNT \
  --policy @inventory-policy.json

# Parse daily reports instead of API calls
```

**Trade-offs**:
- Only updates daily (not hourly)
- Requires additional Azure configuration
- More complex setup

### Option 4: Reduce Metrics Granularity

If you don't need **all** the detailed metrics, simplify:

**Current metrics** (slow):
- Container size (active blobs)
- Deleted blob size
- Snapshot size  
- Version size
- Blob counts for each category

**Simplified approach** (faster):
- Only track active blob size and count
- Skip deleted/snapshots/versions

This could reduce time by ~30-40% by using:
```python
list_blobs()  # Instead of list_blobs(include=['deleted','snapshots','versions'])
```

## Best Configuration for Your Use Case

### For Capacity Monitoring (Not Real-Time)
```yaml
env:
  - name: CACHE_TTL_SECONDS
    value: "3600"        # 1 hour refresh
  - name: MAX_WORKERS
    value: "30"          # Maximum parallelism
resources:
  limits:
    memory: "1Gi"
    cpu: "2000m"
```

**Result**: 
- Cold start: 2-3 minutes
- Prometheus scrapes: < 1 second ✅
- Background refresh: every hour
- Acceptable for capacity planning

### For Cost Tracking (Daily Aggregates)
```yaml
env:
  - name: CACHE_TTL_SECONDS
    value: "21600"       # 6 hours refresh
  - name: MAX_WORKERS
    value: "20"
```

**Result**:
- Refresh only 4 times per day
- Still accurate enough for billing
- Lower Azure API costs

## The Hard Truth

**There is no magic solution** to make Azure blob listing fast because:

1. **Azure API limitation**: No aggregation API exists
2. **Must iterate all blobs**: Required for accurate metrics
3. **Network latency**: Each API call takes time
4. **Data volume**: Millions of blobs = millions of items to process

**The best we can do**:
- ✅ Cache aggressively (done)
- ✅ Parallel processing (done)  
- ✅ Serve stale data while refreshing (done)
- ✅ Tune cache TTL to balance freshness vs performance (configurable)

## Monitoring Strategy

Given the inherent slowness, adjust your monitoring approach:

### What Works Well
✅ **Capacity planning** - hourly/daily trends  
✅ **Cost tracking** - daily/weekly aggregates  
✅ **Growth rate monitoring** - compare day-over-day  
✅ **Waste detection** - identify containers with high deleted/snapshot ratios

### What Doesn't Work Well
❌ **Real-time alerting** - metrics refresh every 30-60 minutes  
❌ **Instant capacity checks** - use Azure Portal instead  
❌ **Live monitoring during incidents** - too slow

## Alternative: Use Azure Monitor Metrics API

For **account-level totals only** (not per-container), Azure provides faster APIs:

```python
# Get account-level capacity (faster, but no container breakdown)
monitor_client.metrics.list(
    resource_uri=storage_account_id,
    metric_names="UsedCapacity",
    timespan="PT1H"
)
```

**Limitation**: Only gives **total account size**, not per-container breakdown.

If you only need account totals, this is **instant** instead of minutes.

## Summary

**Current optimization is the best we can achieve** while maintaining:
- ✅ Per-container metrics
- ✅ Accurate blob counts
- ✅ Deleted/snapshot/version tracking
- ✅ Prometheus compatibility

**Recommended configuration**:
```yaml
CACHE_TTL_SECONDS: "1800"   # 30 minutes (or higher)
MAX_WORKERS: "20"            # High parallelism
# NO sampling (accurate metrics)
```

**Expected behavior**:
- First scrape: 2-5 minutes (one-time cost after pod restart)
- All subsequent scrapes: < 1 second ✅
- Background refresh: every 30 minutes (non-blocking)

This is the **optimal balance** between accuracy and performance given Azure's API limitations.


