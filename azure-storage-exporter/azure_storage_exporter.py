#!/usr/bin/env python3
"""
Azure Storage Account Prometheus Exporter

This exporter collects storage usage metrics from Azure Storage Accounts
and exposes them in Prometheus format.

Metrics exposed:
- azure_storage_container_size_bytes: Size of each container in bytes (active blobs only)
- azure_storage_container_deleted_size_bytes: Size of soft-deleted blobs in each container
- azure_storage_container_snapshot_size_bytes: Size of blob snapshots in each container
- azure_storage_container_version_size_bytes: Size of blob versions in each container
- azure_storage_account_total_size_bytes: Total size of the storage account (active + deleted)
- azure_storage_container_blob_count: Number of active blobs in each container
- azure_storage_container_deleted_blob_count: Number of soft-deleted blobs in each container
- azure_storage_container_snapshot_count: Number of blob snapshots in each container
- azure_storage_container_version_count: Number of blob versions in each container
- azure_storage_exporter_scrape_duration_seconds: Time taken to scrape metrics
- azure_storage_exporter_last_scrape_timestamp: Timestamp of last successful scrape
- azure_storage_exporter_last_azure_fetch_duration_seconds: Duration of the last Azure API fetch
"""

import os
import sys
import time
import logging
import threading
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

from prometheus_client import start_http_server, Gauge, Counter, Histogram
from prometheus_client.core import GaugeMetricFamily, REGISTRY
from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.storage.blob import BlobServiceClient
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.monitor import MonitorManagementClient

# Configure logging (will be set based on LOG_LEVEL env var in main)
logger = logging.getLogger(__name__)


class AzureStorageCollector:
    """Collects Azure Storage metrics and exposes them to Prometheus."""

    def __init__(
        self,
        subscription_id: str,
        storage_account_name: str,
        resource_group_name: str,
        credential=None,
        cache_ttl_seconds: int = 900,  # 15 minutes default cache
        max_workers: int = 10,  # Number of parallel container processing threads
        max_blobs_per_container: int = 0,  # 0 = unlimited, >0 = sample/limit
        use_sampling: bool = False  # If True, use statistical sampling for large containers
    ):
        """
        Initialize the Azure Storage Collector.

        Args:
            subscription_id: Azure subscription ID
            storage_account_name: Name of the storage account to monitor
            resource_group_name: Resource group containing the storage account
            credential: Azure credential object (optional)
            cache_ttl_seconds: How long to cache metrics (default 900s = 15min)
            max_workers: Number of parallel threads for container processing
            max_blobs_per_container: Maximum blobs to process per container (0=unlimited)
            use_sampling: Use statistical sampling for estimation (faster but less accurate)
        """
        self.subscription_id = subscription_id
        self.storage_account_name = storage_account_name
        self.resource_group_name = resource_group_name
        self.credential = credential or DefaultAzureCredential()
        self.cache_ttl_seconds = cache_ttl_seconds
        self.max_workers = max_workers
        self.max_blobs_per_container = max_blobs_per_container
        self.use_sampling = use_sampling
        
        # Cache for storing metrics
        self._cache: Optional[Dict[str, Dict[str, float]]] = None
        self._cache_timestamp: Optional[float] = None
        self._cache_lock = threading.Lock()
        self._refresh_in_progress = False
        
        # Initialize Azure clients
        self._init_clients()
        
        # Prometheus metrics
        self.scrape_duration = Histogram(
            'azure_storage_exporter_scrape_duration_seconds',
            'Time taken to scrape Azure Storage metrics'
        )
        self.scrape_errors = Counter(
            'azure_storage_exporter_scrape_errors_total',
            'Total number of scrape errors'
        )
        self.last_scrape_timestamp = Gauge(
            'azure_storage_exporter_last_scrape_timestamp',
            'Timestamp of last successful scrape'
        )
        self.cache_hits = Counter(
            'azure_storage_exporter_cache_hits_total',
            'Total number of cache hits'
        )
        self.cache_misses = Counter(
            'azure_storage_exporter_cache_misses_total',
            'Total number of cache misses'
        )
        self.cache_age = Gauge(
            'azure_storage_exporter_cache_age_seconds',
            'Age of the cached data in seconds'
        )
        self.last_azure_fetch_duration = Gauge(
            'azure_storage_exporter_last_azure_fetch_duration_seconds',
            'Duration of the last Azure Storage API fetch in seconds'
        )

    def _init_clients(self):
        """Initialize Azure SDK clients."""
        try:
            # Get storage account connection string or use managed identity
            storage_account_url = f"https://{self.storage_account_name}.blob.core.windows.net"
            
            # Check if using storage account key instead of credential
            storage_account_key = os.getenv('AZURE_STORAGE_ACCOUNT_KEY')
            if storage_account_key:
                logger.info("Using Storage Account Key authentication")
                self.blob_service_client = BlobServiceClient(
                    account_url=storage_account_url,
                    credential=storage_account_key
                )
            else:
                self.blob_service_client = BlobServiceClient(
                    account_url=storage_account_url,
                    credential=self.credential
                )
            
            self.storage_client = StorageManagementClient(
                credential=self.credential,
                subscription_id=self.subscription_id
            )
            
            self.monitor_client = MonitorManagementClient(
                credential=self.credential,
                subscription_id=self.subscription_id
            )
            
            logger.info(f"Successfully initialized Azure clients for storage account: {self.storage_account_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Azure clients: {e}", exc_info=True)
            raise

    def _is_cache_valid(self) -> bool:
        """Check if the cache is still valid based on TTL."""
        if self._cache is None or self._cache_timestamp is None:
            return False
        
        age = time.time() - self._cache_timestamp
        return age < self.cache_ttl_seconds
    
    def _get_cached_or_fresh_data(self) -> Dict[str, Dict[str, float]]:
        """
        Get container metrics from cache if valid, otherwise fetch fresh data.
        Implements background refresh to avoid blocking Prometheus scrapes.
        """
        with self._cache_lock:
            # Check if cache is valid
            if self._is_cache_valid():
                cache_age = time.time() - self._cache_timestamp
                self.cache_age.set(cache_age)
                self.cache_hits.inc()
                logger.debug(f"Cache HIT (age: {cache_age:.1f}s, TTL: {self.cache_ttl_seconds}s)")
                return self._cache
            
            # Cache miss or expired
            self.cache_misses.inc()
            logger.info("Cache MISS or expired - fetching fresh data")
            
            # If no cache exists yet, we must block and fetch data
            if self._cache is None:
                logger.info("No cache exists - performing initial blocking fetch")
                fetch_start = time.time()
                containers_data = self._get_container_metrics()
                fetch_duration = time.time() - fetch_start
                self.last_azure_fetch_duration.set(fetch_duration)
                self._cache = containers_data
                self._cache_timestamp = time.time()
                self.cache_age.set(0)
                return containers_data
            
            # Cache exists but is stale - return stale data and trigger background refresh
            if not self._refresh_in_progress:
                logger.info("Triggering background refresh of stale cache")
                self._refresh_in_progress = True
                thread = threading.Thread(target=self._background_refresh, daemon=True)
                thread.start()
            else:
                logger.debug("Background refresh already in progress")
            
            # Return stale cache while refresh happens in background
            cache_age = time.time() - self._cache_timestamp
            self.cache_age.set(cache_age)
            logger.info(f"Returning stale cache (age: {cache_age:.1f}s) while refreshing")
            return self._cache
    
    def _background_refresh(self):
        """Refresh cache in background without blocking Prometheus scrapes."""
        try:
            logger.info("Background refresh started")
            start_time = time.time()
            
            # Fetch fresh data
            containers_data = self._get_container_metrics()
            
            # Calculate duration and update metric
            duration = time.time() - start_time
            self.last_azure_fetch_duration.set(duration)
            
            # Update cache atomically
            with self._cache_lock:
                self._cache = containers_data
                self._cache_timestamp = time.time()
                self._refresh_in_progress = False
                self.cache_age.set(0)
            
            logger.info(f"Background refresh completed in {duration:.2f}s")
            
        except Exception as e:
            logger.error(f"Background refresh failed: {e}", exc_info=True)
            with self._cache_lock:
                self._refresh_in_progress = False

    def collect(self):
        """Collect metrics from Azure Storage Account."""
        start_time = time.time()
        
        try:
            # Get container metrics (from cache or fresh)
            containers_data = self._get_cached_or_fresh_data()
            
            # Container size metric
            container_size_metric = GaugeMetricFamily(
                'azure_storage_container_size_bytes',
                'Size of Azure Storage container in bytes',
                labels=['storage_account', 'container_name', 'resource_group']
            )
            
            # Container blob count metric
            container_blob_count_metric = GaugeMetricFamily(
                'azure_storage_container_blob_count',
                'Number of blobs in Azure Storage container',
                labels=['storage_account', 'container_name', 'resource_group']
            )
            
            # Container deleted blob size metric
            container_deleted_size_metric = GaugeMetricFamily(
                'azure_storage_container_deleted_size_bytes',
                'Size of soft-deleted blobs in Azure Storage container in bytes',
                labels=['storage_account', 'container_name', 'resource_group']
            )
            
            # Container deleted blob count metric
            container_deleted_count_metric = GaugeMetricFamily(
                'azure_storage_container_deleted_blob_count',
                'Number of soft-deleted blobs in Azure Storage container',
                labels=['storage_account', 'container_name', 'resource_group']
            )
            
            # Container snapshot size metric
            container_snapshot_size_metric = GaugeMetricFamily(
                'azure_storage_container_snapshot_size_bytes',
                'Size of blob snapshots in Azure Storage container in bytes',
                labels=['storage_account', 'container_name', 'resource_group']
            )
            
            # Container snapshot count metric
            container_snapshot_count_metric = GaugeMetricFamily(
                'azure_storage_container_snapshot_count',
                'Number of blob snapshots in Azure Storage container',
                labels=['storage_account', 'container_name', 'resource_group']
            )
            
            # Container version size metric
            container_version_size_metric = GaugeMetricFamily(
                'azure_storage_container_version_size_bytes',
                'Size of blob versions in Azure Storage container in bytes',
                labels=['storage_account', 'container_name', 'resource_group']
            )
            
            # Container version count metric
            container_version_count_metric = GaugeMetricFamily(
                'azure_storage_container_version_count',
                'Number of blob versions in Azure Storage container',
                labels=['storage_account', 'container_name', 'resource_group']
            )
            
            # Total account size (active + deleted + snapshots + versions)
            total_size = 0
            total_deleted_size = 0
            total_snapshot_size = 0
            total_version_size = 0
            
            for container_name, metrics in containers_data.items():
                container_size_metric.add_metric(
                    [self.storage_account_name, container_name, self.resource_group_name],
                    metrics['size_bytes']
                )
                container_blob_count_metric.add_metric(
                    [self.storage_account_name, container_name, self.resource_group_name],
                    metrics['blob_count']
                )
                container_deleted_size_metric.add_metric(
                    [self.storage_account_name, container_name, self.resource_group_name],
                    metrics['deleted_size_bytes']
                )
                container_deleted_count_metric.add_metric(
                    [self.storage_account_name, container_name, self.resource_group_name],
                    metrics['deleted_blob_count']
                )
                container_snapshot_size_metric.add_metric(
                    [self.storage_account_name, container_name, self.resource_group_name],
                    metrics['snapshot_size_bytes']
                )
                container_snapshot_count_metric.add_metric(
                    [self.storage_account_name, container_name, self.resource_group_name],
                    metrics['snapshot_count']
                )
                container_version_size_metric.add_metric(
                    [self.storage_account_name, container_name, self.resource_group_name],
                    metrics['version_size_bytes']
                )
                container_version_count_metric.add_metric(
                    [self.storage_account_name, container_name, self.resource_group_name],
                    metrics['version_count']
                )
                total_size += metrics['size_bytes']
                total_deleted_size += metrics['deleted_size_bytes']
                total_snapshot_size += metrics['snapshot_size_bytes']
                total_version_size += metrics['version_size_bytes']
            
            yield container_size_metric
            yield container_blob_count_metric
            yield container_deleted_size_metric
            yield container_deleted_count_metric
            yield container_snapshot_size_metric
            yield container_snapshot_count_metric
            yield container_version_size_metric
            yield container_version_count_metric
            
            # Total account size metric (active blobs only)
            account_size_metric = GaugeMetricFamily(
                'azure_storage_account_total_size_bytes',
                'Total size of Azure Storage account in bytes (active blobs only)',
                labels=['storage_account', 'resource_group']
            )
            account_size_metric.add_metric(
                [self.storage_account_name, self.resource_group_name],
                total_size
            )
            yield account_size_metric
            
            # Total account deleted size metric
            account_deleted_size_metric = GaugeMetricFamily(
                'azure_storage_account_total_deleted_size_bytes',
                'Total size of soft-deleted blobs in Azure Storage account in bytes',
                labels=['storage_account', 'resource_group']
            )
            account_deleted_size_metric.add_metric(
                [self.storage_account_name, self.resource_group_name],
                total_deleted_size
            )
            yield account_deleted_size_metric
            
            # Total account size including deleted metric
            account_total_with_deleted_metric = GaugeMetricFamily(
                'azure_storage_account_total_size_with_deleted_bytes',
                'Total size of Azure Storage account including soft-deleted blobs in bytes',
                labels=['storage_account', 'resource_group']
            )
            account_total_with_deleted_metric.add_metric(
                [self.storage_account_name, self.resource_group_name],
                total_size + total_deleted_size
            )
            yield account_total_with_deleted_metric
            
            # Total account size including ALL (active + deleted + snapshots + versions)
            account_total_all_metric = GaugeMetricFamily(
                'azure_storage_account_total_size_all_bytes',
                'Total size of Azure Storage account including all data (active + deleted + snapshots + versions) in bytes',
                labels=['storage_account', 'resource_group']
            )
            account_total_all_metric.add_metric(
                [self.storage_account_name, self.resource_group_name],
                total_size + total_deleted_size + total_snapshot_size + total_version_size
            )
            yield account_total_all_metric
            
            # Update last scrape timestamp
            self.last_scrape_timestamp.set(time.time())
            
            # Record scrape duration
            duration = time.time() - start_time
            self.scrape_duration.observe(duration)
            logger.info(f"Successfully scraped metrics in {duration:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}", exc_info=True)
            self.scrape_errors.inc()
            raise

    def _process_single_container(self, container_name: str) -> tuple[str, Dict[str, float]]:
        """
        Process a single container to calculate its metrics.
        
        Args:
            container_name: Name of the container to process
            
        Returns:
            Tuple of (container_name, metrics_dict)
        """
        logger.debug(f"Processing container: {container_name}")
        
        # Get container client
        container_client = self.blob_service_client.get_container_client(container_name)
        
        # Initialize counters
        total_size = 0
        blob_count = 0
        deleted_size = 0
        deleted_count = 0
        snapshot_size = 0
        snapshot_count = 0
        version_size = 0
        version_count = 0
        
        try:
            # Get ALL blobs including deleted, snapshots, and versions
            # include=['deleted', 'snapshots', 'versions'] returns everything
            all_blobs = container_client.list_blobs(
                include=['deleted', 'snapshots', 'versions']
            )
            
            # Apply sampling/limiting if configured
            processed_count = 0
            for blob in all_blobs:
                # Check if we should stop processing (sampling mode)
                if self.max_blobs_per_container > 0 and processed_count >= self.max_blobs_per_container:
                    if self.use_sampling:
                        # Estimate total based on sample
                        sample_ratio = processed_count / self.max_blobs_per_container if processed_count > 0 else 1
                        total_size = int(total_size * sample_ratio)
                        blob_count = int(blob_count * sample_ratio)
                        deleted_size = int(deleted_size * sample_ratio)
                        deleted_count = int(deleted_count * sample_ratio)
                        snapshot_size = int(snapshot_size * sample_ratio)
                        snapshot_count = int(snapshot_count * sample_ratio)
                        version_size = int(version_size * sample_ratio)
                        version_count = int(version_count * sample_ratio)
                        logger.info(f"Container '{container_name}': Used sampling (processed {processed_count} blobs, estimated total)")
                    else:
                        logger.warning(f"Container '{container_name}': Stopped at {processed_count} blobs (limit reached)")
                    break
                
                processed_count += 1
                
                # Check blob type
                is_deleted = hasattr(blob, 'deleted') and blob.deleted
                is_snapshot = hasattr(blob, 'snapshot') and blob.snapshot is not None
                is_version = hasattr(blob, 'version_id') and blob.version_id is not None and not hasattr(blob, 'is_current_version')
                
                if is_deleted:
                    # Soft-deleted blob
                    if blob.size:
                        deleted_size += blob.size
                    deleted_count += 1
                elif is_snapshot:
                    # Blob snapshot
                    if blob.size:
                        snapshot_size += blob.size
                    snapshot_count += 1
                elif is_version:
                    # Blob version (non-current)
                    if blob.size:
                        version_size += blob.size
                    version_count += 1
                else:
                    # Current/active blob
                    if blob.size:
                        total_size += blob.size
                    blob_count += 1
                    
        except Exception as e:
            logger.warning(f"Error listing all blobs in container {container_name}: {e}")
            # Fallback to basic listing if full include fails
            try:
                logger.info(f"Trying basic listing for {container_name}")
                blobs = container_client.list_blobs(include=['deleted'])
                for blob in blobs:
                    is_deleted = hasattr(blob, 'deleted') and blob.deleted
                    if is_deleted:
                        if blob.size:
                            deleted_size += blob.size
                        deleted_count += 1
                    else:
                        if blob.size:
                            total_size += blob.size
                        blob_count += 1
            except Exception as e2:
                logger.error(f"Error listing blobs in container {container_name}: {e2}", exc_info=True)
        
        # Calculate totals and waste percentage
        total_blobs = blob_count + deleted_count + snapshot_count + version_count
        total_bytes = total_size + deleted_size + snapshot_size + version_size
        waste_pct = ((deleted_size + snapshot_size + version_size) / total_bytes * 100) if total_bytes > 0 else 0
        
        logger.info(
            f"Container '{container_name}': "
            f"{blob_count:,} active ({total_size / (1024**3):.2f} GiB), "
            f"{deleted_count:,} deleted ({deleted_size / (1024**3):.2f} GiB), "
            f"{snapshot_count:,} snapshots ({snapshot_size / (1024**3):.2f} GiB), "
            f"{version_count:,} versions ({version_size / (1024**3):.2f} GiB), "
            f"waste: {waste_pct:.1f}%"
        )
        
        return container_name, {
            'size_bytes': total_size,
            'blob_count': blob_count,
            'deleted_size_bytes': deleted_size,
            'deleted_blob_count': deleted_count,
            'snapshot_size_bytes': snapshot_size,
            'snapshot_count': snapshot_count,
            'version_size_bytes': version_size,
            'version_count': version_count
        }

    def _get_container_metrics(self) -> Dict[str, Dict[str, float]]:
        """
        Get metrics for all containers in the storage account.
        Uses parallel processing for improved performance.

        Returns:
            Dictionary mapping container names to their metrics
        """
        containers_data = {}
        
        try:
            # List all containers
            container_list = list(self.blob_service_client.list_containers())
            container_count = len(container_list)
            
            logger.info(f"Found {container_count} containers to process")
            
            if container_count == 0:
                logger.warning("No containers found in storage account")
                return containers_data
            
            # Process containers in parallel
            logger.info(f"Processing containers with {self.max_workers} parallel workers")
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all container processing tasks
                future_to_container = {
                    executor.submit(self._process_single_container, container.name): container.name
                    for container in container_list
                }
                
                # Collect results as they complete
                completed = 0
                for future in as_completed(future_to_container):
                    container_name = future_to_container[future]
                    try:
                        name, metrics = future.result()
                        containers_data[name] = metrics
                        completed += 1
                        logger.debug(f"Progress: {completed}/{container_count} containers processed")
                    except Exception as e:
                        logger.error(f"Error processing container {container_name}: {e}", exc_info=True)
        
        except Exception as e:
            logger.error(f"Error getting container metrics: {e}", exc_info=True)
            raise
        
        # Log summary statistics
        total_active_blobs = sum(c['blob_count'] for c in containers_data.values())
        total_active_size = sum(c['size_bytes'] for c in containers_data.values())
        total_deleted_blobs = sum(c['deleted_blob_count'] for c in containers_data.values())
        total_deleted_size = sum(c['deleted_size_bytes'] for c in containers_data.values())
        total_snapshot_count = sum(c['snapshot_count'] for c in containers_data.values())
        total_snapshot_size = sum(c['snapshot_size_bytes'] for c in containers_data.values())
        total_version_count = sum(c['version_count'] for c in containers_data.values())
        total_version_size = sum(c['version_size_bytes'] for c in containers_data.values())
        
        total_size_all = total_active_size + total_deleted_size + total_snapshot_size + total_version_size
        overall_waste = ((total_deleted_size + total_snapshot_size + total_version_size) / total_size_all * 100) if total_size_all > 0 else 0
        
        logger.info(
            f"=== Storage Account Summary === "
            f"Active: {total_active_blobs:,} blobs ({total_active_size / (1024**3):.2f} GiB), "
            f"Deleted: {total_deleted_blobs:,} ({total_deleted_size / (1024**3):.2f} GiB), "
            f"Snapshots: {total_snapshot_count:,} ({total_snapshot_size / (1024**3):.2f} GiB), "
            f"Versions: {total_version_count:,} ({total_version_size / (1024**3):.2f} GiB), "
            f"TOTAL: {total_size_all / (1024**3):.2f} GiB, "
            f"Waste: {overall_waste:.1f}%"
        )
        
        return containers_data


class AzureStorageExporter:
    """Main exporter application."""

    def __init__(self):
        """Initialize the exporter with configuration from environment variables."""
        self.port = int(os.getenv('EXPORTER_PORT', '9358'))
        self.subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID')
        self.storage_account_name = os.getenv('AZURE_STORAGE_ACCOUNT_NAME')
        self.resource_group_name = os.getenv('AZURE_RESOURCE_GROUP_NAME')
        self.scrape_interval = int(os.getenv('SCRAPE_INTERVAL_SECONDS', '300'))
        
        # Cache configuration
        self.cache_ttl_seconds = int(os.getenv('CACHE_TTL_SECONDS', '900'))  # 15 minutes default
        self.max_workers = int(os.getenv('MAX_WORKERS', '10'))  # Parallel container processing
        
        # Performance optimization
        self.max_blobs_per_container = int(os.getenv('MAX_BLOBS_PER_CONTAINER', '0'))  # 0 = unlimited
        self.use_sampling = os.getenv('USE_SAMPLING', 'false').lower() == 'true'
        
        # Optional: Use service principal credentials
        tenant_id = os.getenv('AZURE_TENANT_ID')
        client_id = os.getenv('AZURE_CLIENT_ID')
        client_secret = os.getenv('AZURE_CLIENT_SECRET')
        
        # Validate required environment variables
        self._validate_config()
        
        # Set up credential
        if tenant_id and client_id and client_secret:
            logger.info("Using Service Principal authentication")
            credential = ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret
            )
        else:
            logger.info("Using DefaultAzureCredential (Managed Identity or Azure CLI)")
            credential = DefaultAzureCredential()
        
        # Initialize collector with cache settings and performance options
        self.collector = AzureStorageCollector(
            subscription_id=self.subscription_id,
            storage_account_name=self.storage_account_name,
            resource_group_name=self.resource_group_name,
            credential=credential,
            cache_ttl_seconds=self.cache_ttl_seconds,
            max_workers=self.max_workers,
            max_blobs_per_container=self.max_blobs_per_container,
            use_sampling=self.use_sampling
        )

    def _validate_config(self):
        """Validate required configuration."""
        required_vars = {
            'AZURE_SUBSCRIPTION_ID': self.subscription_id,
            'AZURE_STORAGE_ACCOUNT_NAME': self.storage_account_name,
            'AZURE_RESOURCE_GROUP_NAME': self.resource_group_name
        }
        
        missing_vars = [var for var, value in required_vars.items() if not value]
        
        if missing_vars:
            logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
            sys.exit(1)

    def run(self):
        """Start the exporter server."""
        logger.info(f"Starting Azure Storage Exporter on port {self.port}")
        logger.info(f"Monitoring storage account: {self.storage_account_name}")
        logger.info(f"Resource group: {self.resource_group_name}")
        logger.info(f"Cache TTL: {self.cache_ttl_seconds}s ({self.cache_ttl_seconds/60:.1f} minutes)")
        logger.info(f"Parallel workers: {self.max_workers}")
        if self.max_blobs_per_container > 0:
            sampling_mode = "with sampling" if self.use_sampling else "hard limit"
            logger.info(f"Blob processing limit: {self.max_blobs_per_container} per container ({sampling_mode})")
        else:
            logger.info(f"Blob processing: unlimited (processes all blobs)")
        
        # Register the collector
        REGISTRY.register(self.collector)
        
        # Start HTTP server
        start_http_server(self.port)
        
        logger.info(f"Exporter is running at http://0.0.0.0:{self.port}/metrics")
        logger.info("Press Ctrl+C to stop")
        
        # Keep the process running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down exporter")
            sys.exit(0)


def main():
    """Main entry point."""
    # Configure logging based on LOG_LEVEL environment variable
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    
    if log_level not in valid_log_levels:
        print(f"Warning: Invalid LOG_LEVEL '{log_level}', defaulting to INFO")
        log_level = 'INFO'
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info(f"Log level set to: {log_level}")
    
    try:
        exporter = AzureStorageExporter()
        exporter.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()



