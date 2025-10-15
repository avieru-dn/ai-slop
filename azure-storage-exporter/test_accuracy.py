#!/usr/bin/env python3
"""
Test script to verify Azure Storage blob counting accuracy
Compares our method with Azure Storage Explorer results
"""

import os
import sys
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

# Configuration
STORAGE_ACCOUNT = "dapsrestorageacc"
CONTAINER_NAME = "loki-logs"

def test_blob_counting():
    """Test different methods of counting blobs"""
    
    print(f"Testing blob counting accuracy for {STORAGE_ACCOUNT}/{CONTAINER_NAME}")
    print("=" * 80)
    
    # Initialize client
    account_url = f"https://{STORAGE_ACCOUNT}.blob.core.windows.net"
    credential = DefaultAzureCredential()
    blob_service_client = BlobServiceClient(account_url=account_url, credential=credential)
    container_client = blob_service_client.get_container_client(CONTAINER_NAME)
    
    # Method 1: Active blobs only
    print("\n📊 Method 1: Active blobs only (default list_blobs)")
    active_count = 0
    active_size = 0
    for blob in container_client.list_blobs():
        if blob.size:
            active_size += blob.size
        active_count += 1
    print(f"  Active: {active_count:,} blobs, {active_size / (1024**3):.2f} GiB")
    
    # Method 2: Include deleted (our enhanced method)
    print("\n📊 Method 2: All blobs with include=['deleted']")
    active_count2 = 0
    active_size2 = 0
    deleted_count2 = 0
    deleted_size2 = 0
    
    for blob in container_client.list_blobs(include=['deleted']):
        is_deleted = hasattr(blob, 'deleted') and blob.deleted
        
        if is_deleted:
            if blob.size:
                deleted_size2 += blob.size
            deleted_count2 += 1
        else:
            if blob.size:
                active_size2 += blob.size
            active_count2 += 1
    
    print(f"  Active:  {active_count2:,} blobs, {active_size2 / (1024**3):.2f} GiB")
    print(f"  Deleted: {deleted_count2:,} blobs, {deleted_size2 / (1024**3):.2f} GiB")
    print(f"  Total:   {active_count2 + deleted_count2:,} items, {(active_size2 + deleted_size2) / (1024**3):.2f} GiB")
    
    # Compare with Azure Storage Explorer expected values
    print("\n📊 Azure Storage Explorer (Expected):")
    print(f"  Active:  37,682 blobs, 1.80 GiB")
    print(f"  Deleted: 35,080 blobs, 1.62 GiB") 
    print(f"  Total:   72,762 items, 3.42 GiB")
    
    # Calculate differences
    print("\n📊 Accuracy Check:")
    active_diff = active_count2 - 37682
    deleted_diff = deleted_count2 - 35080
    print(f"  Active diff:  {active_diff:+,} blobs")
    print(f"  Deleted diff: {deleted_diff:+,} blobs")
    
    if abs(active_diff) < 1000 and abs(deleted_diff) < 1000:
        print("\n  ✅ ACCURATE: Within 1000 blobs margin (expected due to time difference)")
    else:
        print("\n  ⚠️  LARGE DIFFERENCE: May indicate pagination or API issues")
    
    # Calculate waste
    total_size = active_size2 + deleted_size2
    waste_pct = (deleted_size2 / total_size * 100) if total_size > 0 else 0
    print(f"\n💰 Storage Waste: {waste_pct:.1f}%")
    print(f"   Cost waste: ~${(deleted_size2 / (1024**3)) * 0.018:.4f}/month (LRS)")

if __name__ == "__main__":
    try:
        test_blob_counting()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
