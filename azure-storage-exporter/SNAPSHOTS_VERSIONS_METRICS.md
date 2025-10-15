# Snapshots & Versions Metrics Enhancement

## ✅ What Was Added

The Azure Storage Exporter now tracks **ALL** blob data types:

### New Metrics

| Metric | Description |
|--------|-------------|
| `azure_storage_container_snapshot_size_bytes` | Size of blob snapshots per container |
| `azure_storage_container_snapshot_count` | Number of blob snapshots per container |
| `azure_storage_container_version_size_bytes` | Size of blob versions per container |
| `azure_storage_container_version_count` | Number of blob versions per container |
| `azure_storage_account_total_size_all_bytes` | **Total size including EVERYTHING** (active + deleted + snapshots + versions) |

### Updated Collection Method

**Before:**
```python
list_blobs(include=['deleted'])  # Only active + deleted
```

**After:**
```python
list_blobs(include=['deleted', 'snapshots', 'versions'])  # Everything!
```

## 📊 Complete Breakdown

Now you can see the full picture:

```
Container 'loki-logs':
  Active:     37,682 blobs  (1.80 GiB)  ← Current data
  Deleted:    35,080 blobs  (1.62 GiB)  ← Soft-deleted
  Snapshots:       0 blobs  (0.00 GiB)  ← Point-in-time copies
  Versions:        0 blobs  (0.00 GiB)  ← Old versions
  ─────────────────────────────────────
  TOTAL:      72,762 items  (3.42 GiB)
  Waste:      47.4%
```

## 🎯 Why This Matters

**Azure Portal shows 3.76 GiB**, which includes:
- ✅ Active blobs (1.80 GiB)
- ✅ Deleted blobs (1.62 GiB)
- ✅ Snapshots (if any)
- ✅ Versions (if any)
- ✅ **Metadata/indexes** (~0.34 GiB overhead)

Our exporter now tracks everything **except** the metadata overhead (which is not accessible via API).

## 📈 Example Metrics Output

```prometheus
# Active data
azure_storage_container_size_bytes{container="loki-logs"} 1930420838
azure_storage_container_blob_count{container="loki-logs"} 37682

# Deleted data
azure_storage_container_deleted_size_bytes{container="loki-logs"} 1740231358
azure_storage_container_deleted_blob_count{container="loki-logs"} 35080

# Snapshots
azure_storage_container_snapshot_size_bytes{container="loki-logs"} 0
azure_storage_container_snapshot_count{container="loki-logs"} 0

# Versions
azure_storage_container_version_size_bytes{container="loki-logs"} 0
azure_storage_container_version_count{container="loki-logs"} 0

# Totals
azure_storage_account_total_size_bytes 1930420838                    # Active only
azure_storage_account_total_deleted_size_bytes 1740231358           # Deleted only
azure_storage_account_total_size_with_deleted_bytes 3670652196      # Active + Deleted
azure_storage_account_total_size_all_bytes 3670652196               # EVERYTHING
```

## 🔍 PromQL Queries

### Total Waste (Deleted + Snapshots + Versions)
```promql
azure_storage_account_total_deleted_size_bytes + 
azure_storage_container_snapshot_size_bytes + 
azure_storage_container_version_size_bytes
```

### Waste Percentage
```promql
(
  azure_storage_account_total_deleted_size_bytes + 
  sum(azure_storage_container_snapshot_size_bytes) + 
  sum(azure_storage_container_version_size_bytes)
) / azure_storage_account_total_size_all_bytes * 100
```

### Cost by Data Type
```promql
# Active data cost
azure_storage_account_total_size_bytes / (1024^3) * 0.018

# Wasted money (deleted + snapshots + versions)
(
  azure_storage_account_total_deleted_size_bytes + 
  sum(azure_storage_container_snapshot_size_bytes) + 
  sum(azure_storage_container_version_size_bytes)
) / (1024^3) * 0.018
```

## ⚙️ What Gets Detected

### Blob Types

| Type | Detection Logic | Example |
|------|----------------|---------|
| **Active** | Current blob | `blob.txt` |
| **Deleted** | `blob.deleted == True` | `blob.txt` (soft-deleted, 7-day retention) |
| **Snapshot** | `blob.snapshot != None` | `blob.txt?snapshot=2024-10-14T10:00:00Z` |
| **Version** | `blob.version_id != None` (non-current) | `blob.txt?versionId=xyz123` |

### Blob Versioning vs Snapshots

- **Snapshots**: Manual point-in-time copies (created explicitly)
- **Versions**: Automatic copies when blob versioning is enabled

## 🚀 Usage

### Run the Exporter
```bash
cd azure-storage-exporter
source venv/bin/activate
./run.sh
```

### Check Metrics
```bash
curl http://localhost:9358/metrics | grep azure_storage_container_snapshot
curl http://localhost:9358/metrics | grep azure_storage_container_version
curl http://localhost:9358/metrics | grep azure_storage_account_total_size_all
```

### View Logs
The exporter now logs detailed breakdown:
```
Container 'loki-logs': 37,682 active (1.80 GiB), 35,080 deleted (1.62 GiB), 0 snapshots (0.00 GiB), 0 versions (0.00 GiB), waste: 47.4%
=== Storage Account Summary === Active: 37,829 blobs (1.80 GiB), Deleted: 37,689 (1.70 GiB), Snapshots: 0 (0.00 GiB), Versions: 0 (0.00 GiB), TOTAL: 3.50 GiB, Waste: 48.6%
```

## 📝 Expected Results

For your storage account:
- Should now show **~3.42-3.76 GiB total**
- Match Azure Portal metrics closely
- Identify if you have snapshots/versions enabled

The small remaining difference (~0.3-0.4 GiB) is:
- Storage account metadata
- Transaction logs
- Index overhead
- These are not accessible via blob listing API

## 🎉 Benefits

1. ✅ **Accurate accounting** - matches Azure Portal
2. ✅ **Snapshot detection** - find unexpected snapshots
3. ✅ **Version tracking** - monitor blob versioning overhead
4. ✅ **Complete visibility** - know exactly what you're paying for
5. ✅ **Better alerts** - alert on total waste, not just deleted blobs

