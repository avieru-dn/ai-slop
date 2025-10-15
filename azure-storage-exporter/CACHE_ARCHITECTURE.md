# Cache Architecture

## Overview Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      Prometheus Scrapes                         │
│                    (every 15-60 seconds)                        │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│              Azure Storage Exporter /metrics                    │
│                                                                 │
│  ┌──────────────────────────────────────────────────────┐     │
│  │          collect() - Prometheus Callback             │     │
│  │                                                       │     │
│  │    ┌─────────────────────────────────────┐           │     │
│  │    │  _get_cached_or_fresh_data()        │           │     │
│  │    │                                     │           │     │
│  │    │  1. Check cache validity            │           │     │
│  │    │     if age < TTL → return cache     │◄──Fast   │     │
│  │    │                                     │   (< 1s)  │     │
│  │    │  2. Cache expired?                  │           │     │
│  │    │     → Return stale cache            │           │     │
│  │    │     → Trigger background refresh    │           │     │
│  │    │                                     │           │     │
│  │    │  3. No cache?                       │           │     │
│  │    │     → Blocking fetch (cold start)   │◄──Slow   │     │
│  │    │                                     │   (2min)  │     │
│  │    └─────────────────────────────────────┘           │     │
│  │                                                       │     │
│  └──────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                 │
                 │  Background Thread (daemon)
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│              _background_refresh()                              │
│                                                                 │
│  ┌──────────────────────────────────────────────────────┐     │
│  │     _get_container_metrics()                         │     │
│  │                                                       │     │
│  │     ThreadPoolExecutor (MAX_WORKERS=10)              │     │
│  │                                                       │     │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐│     │
│  │  │Container│  │Container│  │Container│  │Container││     │
│  │  │    1    │  │    2    │  │    3    │  │   ...   ││     │
│  │  │         │  │         │  │         │  │         ││     │
│  │  │ list_   │  │ list_   │  │ list_   │  │ list_   ││     │
│  │  │ blobs() │  │ blobs() │  │ blobs() │  │ blobs() ││     │
│  │  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘│     │
│  │       │            │            │            │      │     │
│  │       └────────────┴────────────┴────────────┘      │     │
│  │                        │                             │     │
│  │              Aggregate Results                       │     │
│  │                        │                             │     │
│  │                        ▼                             │     │
│  │              Update Cache (atomic)                   │     │
│  │                 with lock                            │     │
│  └──────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Azure Blob Storage API                     │
│                                                                 │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐              │
│  │ Container1 │  │ Container2 │  │ Container3 │  ...         │
│  │  (1M blobs)│  │ (500k blobs│  │  (2M blobs)│              │
│  └────────────┘  └────────────┘  └────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

## Request Flow

### Scenario 1: Cache Hit (Most Common)

```
Time: 0.0s
┌──────────┐
│Prometheus│ Scrape request
│  Scrape  │────────────────────┐
└──────────┘                    │
                                ▼
                    ┌──────────────────────┐
Time: 0.001s        │   Check Cache        │
                    │   age = 300s < 900s  │
                    │   ✓ VALID            │
                    └──────┬───────────────┘
                           │
                           ▼
                    Return cached data
                    ┌──────────────────────┐
Time: 0.5s          │  Metrics Response    │
                    │  (from memory)       │
                    └──────────────────────┘

Total: < 1 second
Cache hit metric incremented
```

### Scenario 2: Cache Expired - Background Refresh

```
Time: 0.0s
┌──────────┐
│Prometheus│ Scrape request
│  Scrape  │────────────────────┐
└──────────┘                    │
                                ▼
                    ┌──────────────────────┐
Time: 0.001s        │   Check Cache        │
                    │   age = 950s > 900s  │
                    │   ✗ EXPIRED          │
                    └──────┬───────────────┘
                           │
                ┌──────────┴───────────┐
                │                      │
                ▼                      ▼
    Return stale cache      Start background thread
    ┌──────────────┐        ┌────────────────────┐
    │  Metrics     │        │  _background_      │
    │  (stale)     │        │   refresh()        │
    └──────────────┘        └────────────────────┘
                                     │
Time: 0.5s                           ▼
    Response sent        ┌──────────────────────┐
                         │  Fetch fresh data    │
                         │  (parallel workers)  │
Time: 2.0min             │  ┌────┐ ┌────┐ ┌────┐│
                         │  │C1  │ │C2  │ │C3  ││
                         │  └────┘ └────┘ └────┘│
                         └──────────┬───────────┘
                                    │
Time: 2.0min                        ▼
                         ┌──────────────────────┐
                         │  Update cache        │
                         │  (atomic with lock)  │
                         └──────────────────────┘
                         
Next scrape gets fresh data!

Scrape response: < 1 second (stale cache served)
Refresh happens: ~2 minutes (in background)
```

### Scenario 3: Cold Start (First Request)

```
Time: 0.0s
┌──────────┐
│Prometheus│ First scrape after startup
│  Scrape  │────────────────────┐
└──────────┘                    │
                                ▼
                    ┌──────────────────────┐
Time: 0.001s        │   Check Cache        │
                    │   cache = None       │
                    │   ✗ NO CACHE         │
                    └──────┬───────────────┘
                           │
                           ▼
                    BLOCKING FETCH
                    ┌──────────────────────┐
Time: 0.1s          │  List containers     │
                    │  (50 containers)     │
                    └──────┬───────────────┘
                           │
                           ▼
                    Parallel processing
                    ┌──────────────────────┐
Time: 0.1s-2min     │ ThreadPoolExecutor   │
                    │ ┌────┐ ┌────┐ ┌────┐ │
                    │ │C1  │ │C2  │ │C3  │ │
                    │ └────┘ └────┘ └────┘ │
                    │   ... 10 workers ... │
                    └──────┬───────────────┘
                           │
                           ▼
                    Process all containers
Time: 2.0min        ┌──────────────────────┐
                    │  Cache result        │
                    │  age = 0s            │
                    └──────┬───────────────┘
                           │
                           ▼
Time: 2.0min        ┌──────────────────────┐
                    │  Return metrics      │
                    └──────────────────────┘

Total: ~2 minutes (one-time cost)
Subsequent requests: < 1 second
```

## Cache State Machine

```
┌─────────────┐
│   START     │
│ (No Cache)  │
└──────┬──────┘
       │
       │ First request (blocking)
       ▼
┌─────────────┐
│   FRESH     │◄────────────────────┐
│  age < TTL  │                     │
└──────┬──────┘                     │
       │                            │
       │ Prometheus scrapes         │
       │ (serve from cache)         │
       │                            │
       ▼                            │
┌─────────────┐                     │
│   VALID     │                     │
│  age < TTL  │                     │
└──────┬──────┘                     │
       │                            │
       │ time passes                │
       │ age >= TTL                 │
       ▼                            │
┌─────────────┐                     │
│   EXPIRED   │                     │
│  age >= TTL │                     │
└──────┬──────┘                     │
       │                            │
       │ Next request               │
       ├─ Return stale cache        │
       │  (non-blocking)            │
       │                            │
       └─ Trigger refresh ──────────┘
          (background thread)
          
```

## Parallel Container Processing

### Sequential Processing (Old)

```
Time: 0s                                                Time: 12m

Container 1 ──────────►│
                       │ Container 2 ──────────►│
                                                │ Container 3 ──────────►│
                                                                         ...
                                                                         
Total time: 10-15 minutes (for 50 containers with millions of blobs)
```

### Parallel Processing (New)

```
Time: 0s         Time: 2m

Container 1  ──────────►│
Container 2  ──────────►│
Container 3  ──────────►│
Container 4  ──────────►│
Container 5  ──────────►│
Container 6  ──────────►│
Container 7  ──────────►│
Container 8  ──────────►│
Container 9  ──────────►│
Container 10 ──────────►│
   ... (all in parallel with 10 workers)

Total time: 2-3 minutes (5-10x faster!)
```

## Thread Safety

### Cache Update Protection

```python
# Multiple threads might try to access cache simultaneously

Thread 1 (Prometheus scrape) ─┐
                               ├──► Lock ──► Read cache ──► Unlock
Thread 2 (Prometheus scrape) ─┘                    

Thread 3 (Background refresh) ───► Lock ──► Update cache ──► Unlock
                                    (waits if locked)

# threading.Lock ensures:
# - No race conditions
# - Atomic cache updates
# - Consistent reads
```

## Cache Metrics Flow

```
┌─────────────────┐
│  Each Request   │
└────────┬────────┘
         │
         ▼
    Check cache
         │
    ┌────┴────┐
    │         │
    ▼         ▼
  Valid    Expired/None
    │         │
    ▼         ▼
cache_hits  cache_misses
   .inc()      .inc()
    │         │
    └────┬────┘
         │
         ▼
    cache_age.set(age)
         │
         ▼
  Return metrics
```

## Performance Comparison

### Without Caching

```
Request 1: ████████████ 12 min
Request 2: ████████████ 12 min
Request 3: ████████████ 12 min
Request 4: ████████████ 12 min

Average: 12 minutes per request
Prometheus scrapes timeout (> 30s)
❌ Metrics unavailable
```

### With Caching (Cold Start)

```
Request 1: ████████████ 2 min (cold start)
Request 2: █ < 1 sec (cached)
Request 3: █ < 1 sec (cached)
Request 4: █ < 1 sec (cached)
Request 5: █ < 1 sec (cached)
...
Request 20: █ < 1 sec (cached)
Request 21: █████████████ 2 min (refresh) + █ < 1 sec (return stale)
Request 22: █ < 1 sec (fresh cache)

Average: < 5 seconds per request
✅ All scrapes succeed
✅ Metrics always available
✅ 95% reduction in API calls
```

## Configuration Impact

### CACHE_TTL_SECONDS

```
TTL = 300s (5 min)
├─ Refresh every 5 minutes
├─ Very fresh data
└─ More Azure API calls

TTL = 900s (15 min) ← Default
├─ Refresh every 15 minutes
├─ Good balance
└─ Reasonable API usage

TTL = 3600s (60 min)
├─ Refresh every hour
├─ Less fresh data
└─ Minimal API calls
```

### MAX_WORKERS

```
MAX_WORKERS = 5
├─ 5 containers processed simultaneously
├─ Lower CPU/memory usage
└─ Slower for many containers

MAX_WORKERS = 10 ← Default
├─ 10 containers processed simultaneously
├─ Balanced resource usage
└─ Good for most use cases

MAX_WORKERS = 30
├─ 30 containers processed simultaneously
├─ Higher CPU/memory usage
└─ Fastest for many containers
```

## Summary

The caching implementation provides:

1. **Immediate responses** to Prometheus scrapes (< 1 second)
2. **Background data refresh** without blocking requests
3. **Parallel container processing** for faster data collection
4. **Thread-safe operations** with proper locking
5. **Observable behavior** through cache metrics
6. **Configurable tuning** via environment variables

This architecture ensures reliable metrics collection even for storage accounts with millions of blobs across hundreds of containers.

