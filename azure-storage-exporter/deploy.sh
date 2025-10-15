#!/bin/bash
set -euo pipefail

# Azure Storage Exporter - Deployment Script
# This script deploys the exporter to Kubernetes

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
K8S_DIR="${SCRIPT_DIR}/k8s"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to check if kubectl is installed
check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        exit 1
    fi
}

# Function to check if required environment variables are set
check_env_vars() {
    local required_vars=(
        "AZURE_SUBSCRIPTION_ID"
        "AZURE_STORAGE_ACCOUNT_NAME"
        "AZURE_RESOURCE_GROUP_NAME"
    )
    
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            missing_vars+=("${var}")
        fi
    done
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        log_error "Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            echo "  - ${var}"
        done
        echo ""
        echo "Please set these variables before running the deployment:"
        echo "  export AZURE_SUBSCRIPTION_ID=<your-subscription-id>"
        echo "  export AZURE_STORAGE_ACCOUNT_NAME=<your-storage-account>"
        echo "  export AZURE_RESOURCE_GROUP_NAME=<your-resource-group>"
        echo ""
        echo "Optional (for Service Principal authentication):"
        echo "  export AZURE_TENANT_ID=<your-tenant-id>"
        echo "  export AZURE_CLIENT_ID=<your-client-id>"
        echo "  export AZURE_CLIENT_SECRET=<your-client-secret>"
        exit 1
    fi
}

# Check prerequisites
log_info "Checking prerequisites..."
check_kubectl
check_env_vars

# Create namespace if it doesn't exist
log_info "Creating namespace..."
kubectl apply -f "${K8S_DIR}/00-namespace.yaml"

# Create service account
log_info "Creating service account..."
kubectl apply -f "${K8S_DIR}/01-serviceaccount.yaml"

# Create or update secret with environment variables
log_info "Creating secret with Azure credentials..."
kubectl create secret generic azure-storage-exporter-credentials \
    --namespace=monitoring \
    --from-literal=AZURE_SUBSCRIPTION_ID="${AZURE_SUBSCRIPTION_ID}" \
    --from-literal=AZURE_STORAGE_ACCOUNT_NAME="${AZURE_STORAGE_ACCOUNT_NAME}" \
    --from-literal=AZURE_RESOURCE_GROUP_NAME="${AZURE_RESOURCE_GROUP_NAME}" \
    --from-literal=AZURE_TENANT_ID="${AZURE_TENANT_ID:-}" \
    --from-literal=AZURE_CLIENT_ID="${AZURE_CLIENT_ID:-}" \
    --from-literal=AZURE_CLIENT_SECRET="${AZURE_CLIENT_SECRET:-}" \
    --from-literal=EXPORTER_PORT="9358" \
    --from-literal=SCRAPE_INTERVAL_SECONDS="300" \
    --dry-run=client -o yaml | kubectl apply -f -

# Deploy the exporter
log_info "Deploying Azure Storage Exporter..."
kubectl apply -f "${K8S_DIR}/03-deployment.yaml"

# Create service
log_info "Creating service..."
kubectl apply -f "${K8S_DIR}/04-service.yaml"

# Create ServiceMonitor (if Prometheus Operator is installed)
if kubectl get crd servicemonitors.monitoring.coreos.com &> /dev/null; then
    log_info "Creating ServiceMonitor..."
    kubectl apply -f "${K8S_DIR}/05-servicemonitor.yaml"
else
    log_warning "ServiceMonitor CRD not found. Skipping ServiceMonitor creation."
    log_warning "Install Prometheus Operator to use ServiceMonitor."
fi

# Create PodMonitor (alternative to ServiceMonitor)
if kubectl get crd podmonitors.monitoring.coreos.com &> /dev/null; then
    log_info "Creating PodMonitor..."
    kubectl apply -f "${K8S_DIR}/06-podmonitor.yaml"
else
    log_warning "PodMonitor CRD not found. Skipping PodMonitor creation."
fi

# Wait for deployment to be ready
log_info "Waiting for deployment to be ready..."
kubectl wait --for=condition=available --timeout=300s \
    deployment/azure-storage-exporter -n monitoring

# Show deployment status
log_info "Deployment status:"
kubectl get pods -n monitoring -l app=azure-storage-exporter

log_info "Deployment completed successfully!"
log_info ""
log_info "To view logs:"
log_info "  kubectl logs -n monitoring -l app=azure-storage-exporter -f"
log_info ""
log_info "To test metrics endpoint:"
log_info "  kubectl port-forward -n monitoring svc/azure-storage-exporter 9358:9358"
log_info "  curl http://localhost:9358/metrics"



