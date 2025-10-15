# Scrape Interval Configuration Guide

## Overview

The Azure Storage Exporter uses **caching** to provide fast metrics to Prometheus. Understanding the relationship between **scrape intervals** and **cache TTL** is critical for optimal performance.

## Key Concepts

### 1. Prometheus Scrape Interval
**What it is**: How often Prometheus/VictoriaMetrics requests metrics from the exporter

**Configured in**: ServiceMonitor/VMServiceScrape
```yaml
spec:
  endpoints:
  - interval: 15m        # Scrape every 15 minutes
    scrapeTimeout: 5m    # Allow up to 5 minutes per scrape
```

### 2. Cache TTL (Time To Live)
**What it is**: How long the exporter caches metrics before refreshing from Azure

**Configured in**: Deployment environment variables
```yaml
env:
  - name: CACHE_TTL_SECONDS
    value: "1800"  # 30 minutes (1800 seconds)
```

### 3. Scrape Timeout
**What it is**: Maximum time Prometheus waits for a response

**Configured in**: ServiceMonitor/VMServiceScrape
```yaml
scrapeTimeout: 5m  # 5 minutes maximum wait time
```

## Recommended Configurations

### Default (Balanced)

**For most use cases** - good balance of freshness and performance:

```yaml
# ServiceMonitor
interval: 15m          # Scrape every 15 minutes
scrapeTimeout: 5m      # Allow 5 minutes for response

# Deployment
CACHE_TTL_SECONDS: "1800"   # 30 minutes cache
```

**How it works**:
- Prometheus scrapes every 15 minutes
- First scrape after cache expires: 2-5 minutes (background refresh starts)
- All other scrapes: < 1 second (served from cache)
- Cache refreshes every 30 minutes in background

**Result**: 
- ✅ Every 2nd scrape gets fresh data (30min / 15min = 2)
- ✅ All scrapes complete successfully
- ✅ Good balance of freshness vs performance

### Large Accounts (Slower Refresh)

**For storage accounts with millions of blobs**:

```yaml
# ServiceMonitor
interval: 30m          # Scrape every 30 minutes
scrapeTimeout: 10m     # Allow 10 minutes for cold start

# Deployment
CACHE_TTL_SECONDS: "3600"   # 1 hour cache
```

**How it works**:
- Prometheus scrapes every 30 minutes
- Cache refreshes every hour
- Every 2nd scrape triggers background refresh
- Stale cache served during refresh

**Result**:
- ✅ Hourly data updates (acceptable for capacity planning)
- ✅ Reduced Azure API costs (fewer calls)
- ✅ Lower resource usage

### Cost Tracking (Minimal Refresh)

**For billing/cost monitoring** (don't need frequent updates):

```yaml
# ServiceMonitor
interval: 1h           # Scrape every hour
scrapeTimeout: 10m

# Deployment
CACHE_TTL_SECONDS: "21600"  # 6 hours cache
```

**How it works**:
- Prometheus scrapes hourly
- Cache refreshes every 6 hours
- Very infrequent Azure API calls

**Result**:
- ✅ 4 updates per day (sufficient for cost tracking)
- ✅ Minimal Azure API costs
- ✅ Minimal resource usage

### High Frequency (Not Recommended)

**Why frequent scraping doesn't help**:

```yaml
# ❌ BAD CONFIGURATION
interval: 1m           # Scrape every minute
CACHE_TTL_SECONDS: "1800"   # 30 minute cache
```

**Problem**: 
- You'll scrape every minute, but get the **same cached data**
- No benefit from frequent scraping
- Wastes Prometheus resources
- Doesn't make data fresher (controlled by cache TTL)

## Configuration Rules

### Rule 1: Scrape Interval Should Be Less Than Cache TTL

**Why**: To get multiple scrapes per cache refresh

```
✅ GOOD:
interval: 15m
CACHE_TTL: 30m
Result: 2 scrapes per refresh (30/15 = 2)

✅ GOOD:
interval: 30m  
CACHE_TTL: 60m
Result: 2 scrapes per refresh (60/30 = 2)

❌ BAD:
interval: 1h
CACHE_TTL: 30m
Result: Every scrape triggers refresh (wasted effort)
```

**Formula**: `Cache TTL / Scrape Interval = Scrapes per Refresh`

**Sweet spot**: 2-4 scrapes per cache refresh

### Rule 2: Scrape Timeout > Initial Scrape Time

**Why**: First scrape after pod restart takes time (cold start)

```yaml
# For large accounts that take 5 minutes on cold start:
scrapeTimeout: 10m   # 2x the expected cold start time

# For small accounts that take 1 minute:
scrapeTimeout: 5m    # 5x the expected time (safety margin)
```

**After first scrape**: Timeout rarely matters (cached responses < 1s)

### Rule 3: Balance Freshness vs Performance

```
More Frequent Refresh (lower TTL):
  ✅ Fresher data
  ❌ More Azure API calls (higher cost)
  ❌ More CPU/memory usage
  ❌ More background processing

Less Frequent Refresh (higher TTL):
  ❌ Staler data
  ✅ Fewer Azure API calls (lower cost)
  ✅ Less CPU/memory usage
  ✅ Less background processing
```

## Configuration Matrix

| Use Case | Scrape Interval | Cache TTL | Scrapes/Refresh | Data Freshness |
|----------|----------------|-----------|-----------------|----------------|
| **Real-time monitoring** | 5m | 15m | 3 | 15 minutes |
| **Capacity planning** | 15m | 30m | 2 | 30 minutes |
| **General monitoring** | 30m | 1h | 2 | 1 hour |
| **Cost tracking** | 1h | 6h | 6 | 6 hours |
| **Daily reports** | 6h | 24h | 4 | 1 day |

## Example Scenarios

### Scenario 1: Fast-Growing Storage Account

**Requirements**:
- Need to detect rapid growth quickly
- Alert if storage increases > 10% in short period

**Configuration**:
```yaml
interval: 10m
scrapeTimeout: 10m
CACHE_TTL_SECONDS: "900"  # 15 minutes
MAX_WORKERS: "30"
```

**Result**: Metrics updated every 15 minutes, scraped every 10 minutes

### Scenario 2: Stable Storage Account

**Requirements**:
- Storage doesn't change rapidly
- Just need daily trend data

**Configuration**:
```yaml
interval: 1h
scrapeTimeout: 10m
CACHE_TTL_SECONDS: "10800"  # 3 hours
MAX_WORKERS: "20"
```

**Result**: Metrics updated every 3 hours, minimal overhead

### Scenario 3: Cost Optimization

**Requirements**:
- Minimize Azure API costs
- Weekly cost reports are sufficient

**Configuration**:
```yaml
interval: 6h
scrapeTimeout: 10m
CACHE_TTL_SECONDS: "43200"  # 12 hours
MAX_WORKERS: "20"
```

**Result**: 
- Only 2 Azure API calls per day
- Significant cost savings
- Still get 4 data points per day

## Monitoring Cache Efficiency

Use these Prometheus queries to verify your configuration:

### Cache Hit Rate
```promql
# Should be > 80% for good configuration
rate(azure_storage_exporter_cache_hits_total[1h]) /
(rate(azure_storage_exporter_cache_hits_total[1h]) + 
 rate(azure_storage_exporter_cache_misses_total[1h]))
```

**Expected values**:
- > 95%: Excellent (most scrapes served from cache)
- 80-95%: Good
- < 80%: Cache TTL might be too short

### Scrape Duration Distribution
```promql
histogram_quantile(0.95, 
  rate(azure_storage_exporter_scrape_duration_seconds_bucket[1h])
)
```

**Expected values**:
- p95 < 2s: Excellent (mostly cached)
- p95 < 30s: Good (occasional refresh)
- p95 > 60s: Check if cache is working

### Cache Age
```promql
azure_storage_exporter_cache_age_seconds
```

**Expected pattern**: Should oscillate between 0 and CACHE_TTL value

## Troubleshooting

### Problem: Scrapes Timing Out

**Symptoms**:
```
Error: context deadline exceeded
Failed scrapes in Prometheus
```

**Solutions**:
1. **Increase scrape timeout**:
   ```yaml
   scrapeTimeout: 10m  # or 15m for very large accounts
   ```

2. **Increase cache TTL** (less frequent heavy refreshes):
   ```yaml
   CACHE_TTL_SECONDS: "3600"
   ```

3. **Increase parallel workers**:
   ```yaml
   MAX_WORKERS: "30"
   ```

### Problem: Stale Metrics

**Symptoms**:
- Metrics not updating frequently enough
- Cache age always near TTL value

**Solutions**:
1. **Decrease cache TTL**:
   ```yaml
   CACHE_TTL_SECONDS: "900"  # 15 minutes instead of 30
   ```

2. **Decrease scrape interval**:
   ```yaml
   interval: 5m  # More frequent scrapes
   ```

### Problem: High Resource Usage

**Symptoms**:
- CPU/memory spikes
- Pod restarts due to OOM

**Solutions**:
1. **Increase cache TTL** (less frequent processing):
   ```yaml
   CACHE_TTL_SECONDS: "3600"
   ```

2. **Reduce parallel workers**:
   ```yaml
   MAX_WORKERS: "10"
   ```

3. **Increase resource limits**:
   ```yaml
   resources:
     limits:
       memory: "2Gi"
       cpu: "2000m"
   ```

### Problem: Background Refresh Failing

**Symptoms**:
```
Cache age keeps increasing beyond TTL
Background refresh errors in logs
```

**Solutions**:
1. **Check Azure API throttling** (429 errors)
2. **Reduce MAX_WORKERS** to lower API rate
3. **Increase CACHE_TTL** to reduce refresh frequency

## Best Practices Summary

1. ✅ **Match intervals**: Scrape interval should be 2-4x less than cache TTL
2. ✅ **Generous timeouts**: Set scrapeTimeout to 2x your expected cold start time
3. ✅ **Start conservative**: Begin with 30m cache TTL, adjust based on needs
4. ✅ **Monitor cache metrics**: Track hit rate and age to validate configuration
5. ✅ **Consider use case**: Cost tracking needs less frequency than capacity alerts
6. ✅ **Resource allocation**: Higher frequency = more resources needed
7. ✅ **Test cold starts**: Ensure first scrape completes within timeout

## Quick Reference

```yaml
# ServiceMonitor: How often Prometheus scrapes
apiVersion: operator.victoriametrics.com/v1beta1
kind: VMServiceScrape
spec:
  endpoints:
  - interval: 15m        # Scrape frequency
    scrapeTimeout: 5m    # Max wait time

# Deployment: How often data refreshes from Azure
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
      - env:
        - name: CACHE_TTL_SECONDS
          value: "1800"      # Refresh frequency (30 minutes)
        - name: MAX_WORKERS
          value: "20"        # Parallelism (speed)
```

**Golden ratio**: `interval < CACHE_TTL < 2 × interval`

Example: `15m < 30m < 30m` ✅


