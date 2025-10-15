# Create Private Link Service via Azure Portal - Step-by-Step Guide

**Service**: Grafana Internal Load Balancer  
**Internal IP**: 10.224.0.28  
**Resource Group**: MC_rg-observability-aks_aks-observability_westus2  
**Date**: October 14, 2025

---

## Prerequisites

✅ **Already Completed:**
- Internal Load Balancer created (`kubernetes-internal`)
- Frontend IP configuration: `10.224.0.28`
- Subnet policies disabled for Private Link Service
- Load balancer serving Grafana on port 3000

---

## Step-by-Step Azure Portal Instructions

### Step 1: Navigate to Private Link Services

1. **Open Azure Portal**: https://portal.azure.com

2. **Search for "Private Link"**:
   - Click the **Search bar** at the top
   - Type: `Private Link`
   - Click on **"Private Link Center"** from results

   ![Search Screenshot](search-private-link.png)

   **Alternative Path:**
   - Click **"All services"** in left menu
   - Under **"Networking"**, click **"Private Link Center"**

---

### Step 2: Start Creating Private Link Service

1. In **Private Link Center**, you'll see the overview page

2. On the left menu, click **"Private link services"**

3. Click the **"+ Create"** or **"+ Add"** button at the top

   ![Private Link Services Page](pls-list.png)

---

### Step 3: Basics Tab

Fill in the following details:

#### **Project Details**

| Field | Value | Notes |
|-------|-------|-------|
| **Subscription** | `DAP_DevOps` | Select subscription ID: `00e10e35-0ad0-427e-893a-72f3b42387c1` |
| **Resource group** | `MC_rg-observability-aks_aks-observability_westus2` | ⚠️ **Must be the node resource group** (starts with `MC_`) |
| **Region** | `West US 2` | Must match load balancer location |

#### **Instance Details**

| Field | Value | Notes |
|-------|-------|-------|
| **Name** | `pls-grafana-observability` | Use a descriptive name |
| **Region** | `West US 2` | Auto-filled from resource group |

**Screenshot Reference:**
```
┌────────────────────────────────────────────────────────┐
│ Create private link service                            │
├────────────────────────────────────────────────────────┤
│ Basics  Outbound settings  Access security  Tags       │
├────────────────────────────────────────────────────────┤
│                                                         │
│ Project details                                         │
│                                                         │
│ Subscription *           [DAP_DevOps ▼]               │
│                                                         │
│ Resource group *         [MC_rg-observability-aks_... ▼]│
│                                                         │
│ Instance details                                        │
│                                                         │
│ Name *                   [pls-grafana-observability]   │
│                                                         │
│ Region *                 [West US 2 ▼]                │
│                                                         │
└────────────────────────────────────────────────────────┘
```

4. Click **"Next: Outbound settings >"**

---

### Step 4: Outbound Settings Tab

This is where you connect the PLS to your internal load balancer.

#### **Load balancer**

| Field | Value | Notes |
|-------|-------|-------|
| **Load balancer** | `kubernetes-internal` | Select from dropdown |

   - Click the dropdown
   - You should see: `kubernetes-internal`
   - Select it

#### **Load balancer frontend IP configuration**

| Field | Value | Notes |
|-------|-------|-------|
| **Frontend IP configuration** | `a676a959c7c924ad29f3af5288885c78 (10.224.0.28)` | This is your Grafana service |

   - Click the dropdown
   - Select the frontend IP that shows `10.224.0.28`
   - The name will be: `a676a959c7c924ad29f3af5288885c78`

#### **Source NAT subnet**

This is where Private Link Service will place its network interfaces.

**Option A: Use Existing Subnet** (Quick)

| Field | Value | Notes |
|-------|-------|-------|
| **Virtual network** | `aks-vnet-38705521` | Auto-populated |
| **Subnet** | `aks-subnet (10.224.0.0/16)` | Your existing AKS subnet |
| **Private IP address settings** | `Dynamic` | Recommended |

**Option B: Create New Subnet** (Best Practice - Recommended)

1. Click **"Manage subnet configuration"** link (opens in new tab)

2. In the new tab, click **"+ Subnet"**

3. Fill in subnet details:
   ```
   Name: snet-private-link-service
   Subnet address range: 10.224.255.0/28
   
   ✅ Enable private link service network policies: OFF (unchecked)
   ```

4. Click **"Save"**

5. Return to previous tab and refresh the subnet dropdown

6. Select: `snet-private-link-service (10.224.255.0/28)`

#### **Enable TCP proxy V2**

| Field | Value | Notes |
|-------|-------|-------|
| **Enable TCP proxy V2** | ☐ Unchecked | Leave disabled unless you need source IP info |

**Screenshot Reference:**
```
┌────────────────────────────────────────────────────────┐
│ Outbound settings                                       │
├────────────────────────────────────────────────────────┤
│                                                         │
│ Load balancer *                                         │
│ [kubernetes-internal ▼]                                │
│                                                         │
│ Load balancer frontend IP configuration *               │
│ [a676a959c7c924ad29f3af5288885c78 (10.224.0.28) ▼]   │
│                                                         │
│ Source NAT subnet                                       │
│ Virtual network *    [aks-vnet-38705521 ▼]            │
│ Subnet *             [aks-subnet ▼]                    │
│                      Manage subnet configuration        │
│                                                         │
│ Private IP address settings                             │
│ ⦿ Dynamic    ○ Static                                  │
│                                                         │
│ ☐ Enable TCP proxy V2                                 │
│                                                         │
└────────────────────────────────────────────────────────┘
```

7. Click **"Next: Access security >"**

---

### Step 5: Access Security Tab

Configure who can create Private Endpoints to your service.

#### **Visibility**

Choose who can **see** your Private Link Service:

**Option A: Role-Based Access Control (Recommended)**
```
⦿ Role-based access control only

Recommended for most scenarios.
Only users with appropriate Azure RBAC permissions
can discover and connect to this Private Link service.
```

**Option B: Restricted by Subscription**
```
○ Restricted by subscription

Allows specific Azure subscriptions to discover and
connect to this service.

Subscriptions:
[+ Add subscription]
```

**Use Case for Option B:**
- If you want to expose Grafana to specific partner/customer subscriptions
- Example: Allow subscription `cda76fc5-a3ee-4c98-b4ba-055125b3de93` (DAP_Dev)

**Recommendation**: Start with **"Role-based access control only"**

#### **Auto-approval**

Choose if Private Endpoint connections are auto-approved or require manual approval:

**Option A: Manual Approval (Recommended for Production)**
```
⦿ Manual approval

All Private Endpoint connection requests will require
manual approval. This gives you control over who
connects to your service.
```

**Option B: Auto-Approval**
```
○ Auto-approval from specific subscriptions

Automatically approve Private Endpoint connections
from these subscriptions:

Subscriptions:
[+ Add subscription]
```

**Recommendation**: Use **"Manual approval"** for security and audit trail

**Screenshot Reference:**
```
┌────────────────────────────────────────────────────────┐
│ Access security                                         │
├────────────────────────────────────────────────────────┤
│                                                         │
│ Visibility                                              │
│                                                         │
│ Who can discover your Private Link service?            │
│                                                         │
│ ⦿ Role-based access control only                       │
│   Recommended. Users with RBAC can discover.           │
│                                                         │
│ ○ Restricted by subscription                           │
│   Specify Azure subscriptions that can discover.       │
│                                                         │
│ Auto-approval                                           │
│                                                         │
│ How should connection requests be handled?             │
│                                                         │
│ ⦿ Manual approval                                      │
│   You must manually approve each connection.           │
│                                                         │
│ ○ Auto-approval from specific subscriptions            │
│   Auto-approve from selected subscriptions.            │
│                                                         │
└────────────────────────────────────────────────────────┘
```

8. Click **"Next: Tags >"**

---

### Step 6: Tags Tab

Add tags for organization and cost tracking:

| Tag Name | Tag Value | Purpose |
|----------|-----------|---------|
| **Environment** | `production` | Environment classification |
| **Service** | `grafana` | Service identifier |
| **ManagedBy** | `devops-team` | Ownership |
| **CostCenter** | `observability` | Cost allocation |
| **Purpose** | `private-link` | Resource purpose |

**Example:**
```
┌─────────────────────────────────────────────┐
│ Tags                                         │
├─────────────────────────────────────────────┤
│                                              │
│ Name              Value                      │
│ Environment       production                 │
│ Service           grafana                    │
│ ManagedBy         devops-team               │
│ CostCenter        observability             │
│ Purpose           private-link              │
│                                              │
│ [+ Add name/value pair]                     │
└─────────────────────────────────────────────┘
```

9. Click **"Next: Review + create >"**

---

### Step 7: Review + Create

1. **Review all settings**:
   - Basics: Name, resource group, region
   - Outbound: Load balancer, frontend IP, subnet
   - Access: Visibility and approval settings
   - Tags: Your organizational tags

2. **Check for validation**:
   - Look for green checkmark: `✓ Validation passed`
   - If validation fails, go back and fix issues

3. **Review cost estimate** (if shown):
   - Private Link Service: ~$7.30/month
   - Data processing: ~$0.01/GB

4. Click **"Create"**

**Screenshot Reference:**
```
┌────────────────────────────────────────────────────────┐
│ ✓ Validation passed                                    │
├────────────────────────────────────────────────────────┤
│                                                         │
│ Basics                                                  │
│ Subscription            DAP_DevOps                     │
│ Resource group          MC_rg-observability-aks_...   │
│ Name                    pls-grafana-observability      │
│ Region                  West US 2                      │
│                                                         │
│ Outbound settings                                       │
│ Load balancer           kubernetes-internal            │
│ Frontend IP config      a676a959c7c924ad29f3af...     │
│ Virtual network         aks-vnet-38705521              │
│ Subnet                  aks-subnet                     │
│                                                         │
│ Access security                                         │
│ Visibility              RBAC only                      │
│ Auto-approval           Manual approval                │
│                                                         │
│                                                         │
│                         [Create]  [< Previous]         │
└────────────────────────────────────────────────────────┘
```

---

### Step 8: Wait for Deployment

1. You'll see: **"Deployment in progress"**
   - This usually takes 1-3 minutes

2. Watch for: **"Your deployment is complete"**

3. Click **"Go to resource"**

---

### Step 9: Get Private Link Service Alias

After creation, you need the **Private Link Service Alias** to share with consumers.

1. In your Private Link Service page, look for **"Properties"** in the left menu

2. Find **"Alias"** - it looks like:
   ```
   pls-grafana-observability.12345678-1234-1234-1234-123456789012.westus2.azure.privatelinkservice
   ```

3. Click the **📋 Copy** icon to copy the alias

4. **Save this alias** - consumers will use it to create Private Endpoints

**Screenshot Reference:**
```
┌────────────────────────────────────────────────────────┐
│ pls-grafana-observability | Properties                 │
├────────────────────────────────────────────────────────┤
│ Search (Ctrl+/)  ︙                                     │
├────────────────────────────────────────────────────────┤
│                                                         │
│ SETTINGS                                                │
│   Properties                                            │
│   IP configurations                                     │
│   Private endpoint connections                          │
│                                                         │
│ Essentials                                              │
│                                                         │
│ Resource group                                          │
│ MC_rg-observability-aks_aks-observability_westus2      │
│                                                         │
│ Location                                                │
│ West US 2                                               │
│                                                         │
│ Alias                                                   │
│ pls-grafana-observability.abc123...westus2.azure... 📋 │
│                                                         │
│ Resource ID                                             │
│ /subscriptions/00e10e35-0ad0-427e-893a-72f3b4238... 📋 │
│                                                         │
└────────────────────────────────────────────────────────┘
```

---

## Post-Creation: Verify Private Link Service

### Check Private Link Service Status

1. In the **Private Link Service** page, click **"IP configurations"** (left menu)

2. You should see:
   - **Name**: Auto-generated (e.g., `nic-pls-grafana...`)
   - **Private IP address**: Allocated from your subnet
   - **Provisioning state**: `Succeeded`

### View Network Interface

1. Click **"IP configurations"** to see the network interface(s)

2. You can click on the IP configuration to see more details

---

## How to Share Access (For Consumers)

When someone wants to connect to your Grafana via Private Endpoint:

### Option 1: Share Alias (If RBAC Only)

Send them the **alias** (copied in Step 9):
```
pls-grafana-observability.12345678-1234-1234-1234-123456789012.westus2.azure.privatelinkservice
```

### Option 2: Share Resource ID (Alternative)

Send them the **Resource ID**:
```
/subscriptions/00e10e35-0ad0-427e-893a-72f3b42387c1/resourceGroups/MC_rg-observability-aks_aks-observability_westus2/providers/Microsoft.Network/privateLinkServices/pls-grafana-observability
```

### They will then:

1. Create a **Private Endpoint** in their subscription/VNet
2. Use your alias or resource ID
3. Submit connection request (if manual approval)
4. You approve the request (see next section)

---

## Approve Private Endpoint Connections

### View Connection Requests

1. In your **Private Link Service** page
2. Click **"Private endpoint connections"** (left menu)
3. You'll see pending connections with status: `Pending`

### Approve a Connection

1. Select the connection request
2. Click **"Approve"** at the top
3. Add optional message:
   ```
   Approved for DAP_Dev team access to Grafana observability.
   ```
4. Click **"Yes"**

### Reject a Connection

1. Select the connection request
2. Click **"Reject"** at the top
3. Add rejection reason:
   ```
   Unauthorized access attempt.
   ```
4. Click **"Yes"**

**Screenshot Reference:**
```
┌────────────────────────────────────────────────────────┐
│ Private endpoint connections                            │
├────────────────────────────────────────────────────────┤
│ [✓ Approve]  [✗ Reject]  [🗑 Remove]  [↻ Refresh]     │
├────────────────────────────────────────────────────────┤
│                                                         │
│ ☐ Name                 Status    Subscription          │
│ ☐ pe-grafana-dev       Pending   DAP_Dev              │
│ ☐ pe-grafana-prod      Approved  DAP_Prod             │
│                                                         │
└────────────────────────────────────────────────────────┘
```

---

## Testing the Private Link Service

### From Consumer Side (After Private Endpoint Created)

Once someone creates a Private Endpoint and you approve it:

```bash
# From their VNet, they can access:
curl http://10.x.x.x:3000

# Where 10.x.x.x is their Private Endpoint's private IP
```

### Check Connection Status

1. Go to **Private Link Service** → **Private endpoint connections**
2. Click on an approved connection
3. View details:
   - Connection state: `Approved`
   - Private endpoint name
   - Consumer's VNet/subscription

---

## Monitoring and Management

### View Metrics

1. In **Private Link Service** page
2. Click **"Metrics"** (left menu)
3. Add metrics:
   - **Bytes In**
   - **Bytes Out**
   - **Active Connections**
   - **Packets Dropped**

### View Activity Logs

1. Click **"Activity log"** (left menu)
2. See all operations:
   - Private Endpoint connection approvals
   - Configuration changes
   - Who made changes and when

### Set Up Alerts

1. Click **"Alerts"** (left menu)
2. Click **"+ Create alert rule"**
3. Create alerts for:
   - New Private Endpoint connection requests
   - Connection failures
   - High traffic volume

---

## Clean Up / Delete Private Link Service

**⚠️ Warning**: Deleting the PLS will break all existing Private Endpoint connections!

### Steps to Delete:

1. Navigate to your **Private Link Service**
2. Click **"Overview"**
3. Click **"Delete"** at the top
4. Confirm by typing the resource name
5. Click **"Delete"**

**Before Deleting:**
- ✓ Notify all consumers
- ✓ Check **"Private endpoint connections"** to see who's connected
- ✓ Remove or reject all connections first (optional but recommended)

---

## Troubleshooting

### Issue: "Cannot create Private Link Service"

**Cause**: Subnet policies not disabled

**Solution**:
1. Go to **Virtual Network** → **Subnets** → Select your subnet
2. Scroll down to **Private link service network policies**
3. Set to: `Disabled`
4. Click **"Save"**

### Issue: "Load balancer not found in dropdown"

**Cause**: Wrong resource group selected

**Solution**:
- Make sure you're in the **node resource group** (starts with `MC_`)
- Resource group: `MC_rg-observability-aks_aks-observability_westus2`

### Issue: "Frontend IP configuration not showing"

**Cause**: Load balancer has no internal frontend IPs

**Solution**:
- Verify your Kubernetes service has annotation:
  ```yaml
  service.beta.kubernetes.io/azure-load-balancer-internal: "true"
  ```
- Check that the load balancer type is `internal` not `public`

### Issue: "Private Endpoint connection stuck in Pending"

**Cause**: Manual approval required

**Solution**:
1. Go to Private Link Service
2. Click **"Private endpoint connections"**
3. Select the pending connection
4. Click **"Approve"**

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│              Consumer Subscription (DAP_Dev)                 │
│                                                              │
│  ┌──────────────────────────────────────────────────┐      │
│  │  Consumer VNet: 10.30.0.0/16                     │      │
│  │                                                   │      │
│  │  ┌─────────────────────────────────────────┐    │      │
│  │  │  Private Endpoint                        │    │      │
│  │  │  Private IP: 10.30.5.10                 │    │      │
│  │  └──────────────┬──────────────────────────┘    │      │
│  │                 │                                 │      │
│  └─────────────────┼─────────────────────────────────┘      │
│                    │                                         │
└────────────────────┼─────────────────────────────────────────┘
                     │
              Azure Backbone Network
              (Private Connection)
                     │
┌────────────────────▼─────────────────────────────────────────┐
│       Provider Subscription (DAP_DevOps)                      │
│                                                              │
│  ┌──────────────────────────────────────────────────┐      │
│  │  Provider VNet: 10.224.0.0/12                    │      │
│  │                                                   │      │
│  │  ┌─────────────────────────────────────────┐    │      │
│  │  │  Private Link Service                    │    │      │
│  │  │  pls-grafana-observability              │    │      │
│  │  └──────────────┬──────────────────────────┘    │      │
│  │                 │                                 │      │
│  │  ┌──────────────▼──────────────────────────┐    │      │
│  │  │  Internal Load Balancer                  │    │      │
│  │  │  IP: 10.224.0.28                        │    │      │
│  │  └──────────────┬──────────────────────────┘    │      │
│  │                 │                                 │      │
│  │       ┏━━━━━━━━━▼━━━━━━━━┓                      │      │
│  │       ┃  Grafana Pod      ┃                      │      │
│  │       ┃  10.224.0.161     ┃                      │      │
│  │       ┗━━━━━━━━━━━━━━━━━━━┛                      │      │
│  │                                                   │      │
│  └──────────────────────────────────────────────────┘      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Summary of Your Configuration

| Setting | Value |
|---------|-------|
| **Private Link Service Name** | `pls-grafana-observability` |
| **Resource Group** | `MC_rg-observability-aks_aks-observability_westus2` |
| **Region** | `West US 2` |
| **Load Balancer** | `kubernetes-internal` |
| **Frontend IP** | `10.224.0.28` |
| **VNet** | `aks-vnet-38705521` |
| **Subnet** | `aks-subnet (10.224.0.0/16)` |
| **Service** | Grafana (port 3000) |
| **Visibility** | RBAC only (recommended) |
| **Auto-approval** | Manual (recommended) |

---

## Related Documentation

- [AKS Internal Load Balancer Guide](./aks-internal-loadbalancer-guide.md)
- [Azure Private Link Service Guide (CLI)](./azure-private-link-service-guide.md)
- [VNet Analysis and Risks](./vnet-analysis-and-risks.md)

---

## Quick Reference Links

- **Azure Portal Private Link**: https://portal.azure.com/#view/Microsoft_Azure_Network/PrivateLinkCenterBlade
- **Your Resource Group**: https://portal.azure.com/#@/resource/subscriptions/00e10e35-0ad0-427e-893a-72f3b42387c1/resourceGroups/MC_rg-observability-aks_aks-observability_westus2/overview
- **Load Balancers**: https://portal.azure.com/#view/HubsExtension/BrowseResource/resourceType/Microsoft.Network%2FloadBalancers

---

**Document Owner**: DevOps/SRE Team  
**Last Updated**: October 14, 2025  
**Service**: Grafana Observability Cluster


