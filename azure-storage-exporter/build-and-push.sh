#!/bin/bash
set -euo pipefail

# Azure Storage Exporter - Build and Push Script
# This script builds the Docker image and pushes it to Azure Container Registry

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_NAME="sre-images/azure-storage-exporter"
IMAGE_TAG="${IMAGE_TAG:-latest}"

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

# Check if ACR name is provided
if [ -z "${ACR_NAME:-}" ]; then
    log_error "ACR_NAME environment variable is not set"
    echo "Usage: ACR_NAME=myregistry IMAGE_TAG=v1.0.0 ./build-and-push.sh"
    exit 1
fi

FULL_IMAGE_NAME="${ACR_NAME}.azurecr.io/${IMAGE_NAME}:${IMAGE_TAG}"

log_info "Building Azure Storage Exporter Docker image"
log_info "Image: ${FULL_IMAGE_NAME}"

# Navigate to script directory
cd "${SCRIPT_DIR}"

# Login to ACR first (required for buildx --push)
log_info "Logging in to Azure Container Registry: ${ACR_NAME}"
az acr login --name "${ACR_NAME}"

if [ $? -eq 0 ]; then
    log_info "Successfully logged in to ACR"
else
    log_error "Failed to login to ACR"
    exit 1
fi

# Check if buildx is available
if ! docker buildx version &> /dev/null; then
    log_error "Docker buildx is not available. Please update Docker Desktop."
    exit 1
fi

# Create or use existing buildx builder with multi-platform support
BUILDER_NAME="multiarch-builder"
if ! docker buildx inspect "${BUILDER_NAME}" &> /dev/null; then
    log_info "Creating buildx builder for multi-platform builds..."
    docker buildx create --name "${BUILDER_NAME}" --use --bootstrap
else
    log_info "Using existing buildx builder: ${BUILDER_NAME}"
    docker buildx use "${BUILDER_NAME}"
fi

# Build and push the Docker image for AMD64 (AKS default architecture)
log_info "Building and pushing multi-platform Docker image for linux/amd64..."
docker buildx build \
    --platform linux/amd64 \
    --tag "${FULL_IMAGE_NAME}" \
    --push \
    .

if [ $? -eq 0 ]; then
    log_info "Docker image built and pushed successfully: ${FULL_IMAGE_NAME}"
else
    log_error "Failed to build and push Docker image"
    exit 1
fi

# Also tag as latest if not already
if [ "${IMAGE_TAG}" != "latest" ]; then
    LATEST_IMAGE="${ACR_NAME}.azurecr.io/${IMAGE_NAME}:latest"
    log_info "Building and pushing latest tag: ${LATEST_IMAGE}"
    docker buildx build \
        --platform linux/amd64 \
        --tag "${LATEST_IMAGE}" \
        --push \
        .
fi

log_info "Build and push completed successfully!"
log_info "You can now deploy using: kubectl apply -f k8s/"



