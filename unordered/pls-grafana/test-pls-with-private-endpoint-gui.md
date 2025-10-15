# Test Private Link Service by Creating Private Endpoint - Azure Portal Guide

**Private Link Service**: `avieru-pls-test`  
**PLS Alias**: `avieru-pls-test.12fb82b0-7152-4d74-a8f0-d0638172e3bb.westus2.azure.privatelinkservice`  
**Service**: Grafana Internal (10.224.0.28:3000)  
**Date**: October 14, 2025

---

## Understanding the Test Flow

```
┌──────────────────────────────────────────────────────────┐
│ YOU ARE HERE → Creating Private Endpoint (Test)          │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  Your VNet: aks-vnet-38705521 (10.224.0.0/12)          │
│                                                           │
│  ┌────────────────────────────────────────┐             │
│  │ Private Endpoint                        │             │
│  │ Name: pe-test-grafana                  │             │
│  │ Subnet: aks-appgateway (10.238.0.0/24) │             │
│  │ Private IP: 10.238.0.X (auto-assigned) │             │
│  └──────────────┬─────────────────────────┘             │
│                 │                                         │
│                 │ Private Link Connection                 │
│                 │ (Through Azure Backbone)                │
│                 ▼                                         │
│  ┌────────────────────────────────────────┐             │
│  │ Private Link Service                    │             │
│  │ Name: avieru-pls-test                  │             │
│  └──────────────┬─────────────────────────┘             │
│                 │                                         │
│                 ▼                                         │
│  ┌────────────────────────────────────────┐             │
│  │ Internal Load Balancer                  │             │
│  │ IP: 10.224.0.28                        │             │
│  └──────────────┬─────────────────────────┘             │
│                 │                                         │
│                 ▼                                         │
│            Grafana Pod                                    │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

---

## Step-by-Step: Create Private Endpoint in Azure Portal

### Step 1: Navigate to Private Endpoints

1. **Open Azure Portal**: https://portal.azure.com

2. **Search for "Private endpoints"**:
   - Click the **Search bar** at the top
   - Type: `Private endpoints`
   - Click on **"Private endpoints"** from results

   **Alternative Path:**
   - All services → Networking → **Private endpoints**

---

### Step 2: Start Creating Private Endpoint

1. Click **"+ Create"** or **"+ Add"** button at the top

---

### Step 3: Basics Tab

Fill in the following details:

#### **Project Details**

| Field | Value | Notes |
|-------|-------|-------|
| **Subscription** | `DAP_DevOps` | Subscription: `00e10e35-0ad0-427e-893a-72f3b42387c1` |
| **Resource group** | `MC_rg-observability-aks_aks-observability_westus2` | Same as your PLS (for testing) |

#### **Instance Details**

| Field | Value | Notes |
|-------|-------|-------|
| **Name** | `pe-test-grafana` | Descriptive name |
| **Network Interface Name** | `pe-test-grafana-nic` | Auto-generated, leave default |
| **Region** | `West US 2` | Must match PLS region |

**Screenshot Reference:**
```
┌────────────────────────────────────────────────────────┐
│ Create a private endpoint                              │
├────────────────────────────────────────────────────────┤
│ Basics  Resource  Virtual Network  DNS  Tags           │
├────────────────────────────────────────────────────────┤
│                                                         │
│ Project details                                         │
│                                                         │
│ Subscription *           [DAP_DevOps ▼]               │
│                                                         │
│ Resource group *         [MC_rg-observability-aks... ▼]│
│                                                         │
│ Instance details                                        │
│                                                         │
│ Name *                   [pe-test-grafana]             │
│                                                         │
│ Network Interface Name   [pe-test-grafana-nic]         │
│                                                         │
│ Region *                 [West US 2 ▼]                │
│                                                         │
└────────────────────────────────────────────────────────┘
```

2. Click **"Next: Resource >"**

---

### Step 4: Resource Tab

This is where you connect to your Private Link Service.

#### **Connection Method**

Select: **"Connect to an Azure resource by resource ID or alias"**

```
○ Connect to an Azure resource in my directory
⦿ Connect to an Azure resource by resource ID or alias
```

#### **Resource**

| Field | Value |
|-------|-------|
| **Resource ID or alias** | `avieru-pls-test.12fb82b0-7152-4d74-a8f0-d0638172e3bb.westus2.azure.privatelinkservice` |

**Paste your PLS alias exactly as shown above** ⬆️

#### **Request Message**

| Field | Value |
|-------|-------|
| **Request message** | `Test connection for Grafana observability access` |

This message will be shown to you (the PLS owner) when you approve the connection.

**Screenshot Reference:**
```
┌────────────────────────────────────────────────────────┐
│ Resource                                                │
├────────────────────────────────────────────────────────┤
│                                                         │
│ Connection method                                       │
│                                                         │
│ ○ Connect to an Azure resource in my directory         │
│ ⦿ Connect to an Azure resource by resource ID or alias │
│                                                         │
│ Resource                                                │
│                                                         │
│ Resource ID or alias *                                  │
│ [avieru-pls-test.12fb82b0-7152-4d74-a8f0-d063...]    │
│                                                         │
│ Request message                                         │
│ [Test connection for Grafana observability access]     │
│                                                         │
└────────────────────────────────────────────────────────┘
```

3. Click **"Next: Virtual Network >"**

---

### Step 5: Virtual Network Tab

Choose where to place the Private Endpoint in your network.

#### **Networking**

| Field | Value | Notes |
|-------|-------|-------|
| **Virtual network** | `aks-vnet-38705521` | Your AKS VNet |
| **Subnet** | `aks-appgateway (10.238.0.0/24)` | ⚠️ Use a **different** subnet than PLS |

**Why use a different subnet?**
- Your PLS is using `aks-subnet (10.224.0.0/16)`
- Private Endpoint should be in a different subnet for testing
- `aks-appgateway` subnet is perfect for this

#### **Private IP Configuration**

```
⦿ Dynamically allocate IP address
○ Statically allocate IP address
```

**Recommendation**: Use **Dynamic** for testing

#### **Application security group**

Leave empty (optional)

**Screenshot Reference:**
```
┌────────────────────────────────────────────────────────┐
│ Virtual Network                                         │
├────────────────────────────────────────────────────────┤
│                                                         │
│ Networking                                              │
│                                                         │
│ Virtual network *        [aks-vnet-38705521 ▼]        │
│                                                         │
│ Subnet *                 [aks-appgateway ▼]            │
│                          10.238.0.0/24                  │
│                                                         │
│ Private IP configuration                                │
│                                                         │
│ ⦿ Dynamically allocate IP address                      │
│ ○ Statically allocate IP address                       │
│                                                         │
│ Application security group                              │
│ [None selected]                                         │
│                                                         │
└────────────────────────────────────────────────────────┘
```

4. Click **"Next: DNS >"**

---

### Step 6: DNS Tab

#### **Integrate with private DNS zone**

For testing, you can skip this:

```
☐ Integrate with private DNS zone
```

**Why skip for testing?**
- DNS integration is not needed for IP-based testing
- You'll test using the Private Endpoint's IP address directly
- You can add DNS later if needed

**Screenshot Reference:**
```
┌────────────────────────────────────────────────────────┐
│ DNS                                                     │
├────────────────────────────────────────────────────────┤
│                                                         │
│ ☐ Integrate with private DNS zone                     │
│                                                         │
│   When enabled, creates DNS records automatically      │
│                                                         │
└────────────────────────────────────────────────────────┘
```

5. Click **"Next: Tags >"**

---

### Step 7: Tags Tab

Add tags for organization:

| Tag Name | Tag Value |
|----------|-----------|
| **Environment** | `test` |
| **Service** | `grafana` |
| **Purpose** | `pls-testing` |

6. Click **"Next: Review + create >"**

---

### Step 8: Review + Create

1. **Review all settings**:
   - Basics: Name, region, resource group
   - Resource: PLS alias
   - Virtual Network: VNet and subnet
   - DNS: Not integrated (for testing)

2. **Check for validation**:
   - Look for: `✓ Validation passed`

3. Click **"Create"**

---

### Step 9: Wait for Deployment

**Deployment will take 1-3 minutes**

You'll see: **"Deployment in progress"**

---

### Step 10: Approve the Private Endpoint Connection

Since your PLS is configured with **manual approval**, you need to approve the connection.

#### **Navigate to Your Private Link Service**

1. Go to **Private Link Center** → **Private link services**
2. Click on **`avieru-pls-test`**

#### **View Pending Connection**

1. In the left menu, click **"Private endpoint connections"**
2. You should see:
   ```
   Name: pe-test-grafana
   Status: Pending
   Connection State: Pending
   ```

#### **Approve the Connection**

1. **Select** the `pe-test-grafana` connection (checkbox)
2. Click **"Approve"** at the top
3. Add approval message (optional):
   ```
   Approved for testing Private Link Service functionality
   ```
4. Click **"Yes"**

**Wait 30-60 seconds** for approval to complete

5. Refresh the page - Status should change to: **"Approved"**

---

### Step 11: Get Private Endpoint IP Address

Now find the IP address assigned to your Private Endpoint:

1. Go back to **Private endpoints**
2. Click on **`pe-test-grafana`**
3. Click **"Properties"** in the left menu
4. Look for **"Private IP address"**:
   ```
   Example: 10.238.0.5
   ```

5. **Copy this IP address** - you'll use it to test!

**Alternative way to get IP:**
1. In the Private Endpoint page
2. Click **"Network interface"** in the left menu
3. Click on the NIC name (e.g., `pe-test-grafana-nic`)
4. See **"Private IP address"** in the overview

---

## Testing Your Private Link Service

### **From a Pod in Your AKS Cluster**

Now you can test using the Private Endpoint's private IP:

```bash
# Get into a pod in your cluster
kubectl exec -it -n grafana-test grafana-85bf4fb56b-dkkvn -- sh

# Test using the Private Endpoint IP (replace with your actual IP)
curl http://10.238.0.5:3000

# Or test with verbose output
curl -v http://10.238.0.5:3000

# Test with header info
curl -I http://10.238.0.5:3000
```

**Expected Result:**
```html
<a href="/login">Found</a>
```
or
```
HTTP/1.1 302 Found
Location: /login
...
```

### **What This Tests:**

```
Your Grafana Pod
    ↓
curl http://10.238.0.5:3000
    ↓
Private Endpoint (10.238.0.5 in aks-appgateway subnet)
    ↓
Private Link Connection (Azure Backbone)
    ↓
Private Link Service (avieru-pls-test)
    ↓
Internal Load Balancer (10.224.0.28)
    ↓
Grafana Pod (10.224.0.161)
    ↓
Response back through the chain
```

---

## Troubleshooting

### Issue 1: Connection Shows "Pending" Forever

**Cause**: You haven't approved the connection

**Solution**: Go to PLS → Private endpoint connections → Select → Approve

---

### Issue 2: "Connection timeout" when curling PE IP

**Possible Causes:**

**A) NSG Blocking Traffic**
```bash
# Check NSG rules on aks-appgateway subnet
az network vnet subnet show \
  --resource-group MC_rg-observability-aks_aks-observability_westus2 \
  --vnet-name aks-vnet-38705521 \
  --name aks-appgateway \
  --query "networkSecurityGroup.id"
```

**B) Wrong Port**
- Ensure you're using port `3000` (Grafana's port)
- Check: `curl http://10.238.0.5:3000` not `:80` or `:443`

**C) Private Endpoint Not Approved**
- Verify connection status is "Approved" not "Pending"

---

### Issue 3: DNS Resolution Error

If you tried to use DNS and it failed:

**Cause**: You didn't integrate with Private DNS zone

**Solution**: For testing, **use IP address directly**, not DNS name

---

### Issue 4: "Could not resolve host"

**Cause**: Trying to curl the PLS alias directly

**Solution**: 
- ❌ DON'T: `curl avieru-pls-test.12fb82b0-7152...`
- ✅ DO: `curl http://<private-endpoint-ip>:3000`

The alias is NOT a DNS name - it's a resource identifier for creating Private Endpoints.

---

## Verification Checklist

Before testing, verify:

- [ ] Private Endpoint created successfully
- [ ] Connection status: **Approved** (in PLS page)
- [ ] Private Endpoint has an IP address assigned
- [ ] You're using the correct IP address
- [ ] You're using port 3000
- [ ] Testing from within the same VNet (or peered VNet)

---

## Architecture Diagram (What You Built)

```
┌─────────────────────────────────────────────────────────┐
│  Your AKS VNet: aks-vnet-38705521 (10.224.0.0/12)     │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │  aks-appgateway Subnet (10.238.0.0/24)         │    │
│  │                                                 │    │
│  │  ┌─────────────────────────────────────────┐  │    │
│  │  │  Private Endpoint: pe-test-grafana      │  │    │
│  │  │  IP: 10.238.0.5                         │  │    │
│  │  └──────────────┬──────────────────────────┘  │    │
│  └─────────────────┼─────────────────────────────┘    │
│                    │                                    │
│                    │ Private Link Connection            │
│                    │ (Azure Backbone Network)           │
│                    │                                    │
│  ┌─────────────────▼─────────────────────────────┐    │
│  │  Private Link Service                          │    │
│  │  Name: avieru-pls-test                        │    │
│  │  (in aks-subnet)                              │    │
│  └──────────────┬─────────────────────────────────┘    │
│                 │                                       │
│  ┌──────────────▼──────────────────────────────┐      │
│  │  aks-subnet (10.224.0.0/16)                 │      │
│  │                                              │      │
│  │  ┌────────────────────────────────────┐    │      │
│  │  │  Internal Load Balancer             │    │      │
│  │  │  kubernetes-internal                │    │      │
│  │  │  IP: 10.224.0.28                   │    │      │
│  │  └──────────────┬─────────────────────┘    │      │
│  │                 │                            │      │
│  │       ┏━━━━━━━━━▼━━━━━━━┓                  │      │
│  │       ┃  Grafana Pod     ┃                  │      │
│  │       ┃  10.224.0.161    ┃                  │      │
│  │       ┗━━━━━━━━━━━━━━━━━━┛                  │      │
│  └──────────────────────────────────────────────┘      │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## Success Criteria

Your Private Link Service is working if:

✅ Private Endpoint created successfully  
✅ Connection approved in PLS  
✅ Private Endpoint has IP assigned  
✅ `curl http://<PE-IP>:3000` returns Grafana response  
✅ You can access Grafana UI via Private Endpoint IP  

---

## Cleanup (After Testing)

If you want to remove the test resources:

### Delete Private Endpoint
1. Go to **Private endpoints**
2. Select **`pe-test-grafana`**
3. Click **"Delete"** at the top
4. Confirm deletion

**Note**: The Private Link Service can stay - it's ready for real consumers!

---

## Next Steps

### **For Production Use:**

1. **Share PLS Alias** with consumers:
   ```
   avieru-pls-test.12fb82b0-7152-4d74-a8f0-d0638172e3bb.westus2.azure.privatelinkservice
   ```

2. **Approve Their Connections**:
   - They create Private Endpoints in their VNets
   - You approve their connection requests
   - They access via their Private Endpoint IP

3. **Set Up DNS** (Optional):
   - Create Private DNS zone
   - Add A record pointing to Private Endpoint IP
   - Use friendly name: `grafana.internal.example.com`

---

## Summary

| What You Did | Result |
|--------------|--------|
| Created Private Link Service | ✅ `avieru-pls-test` exposing Grafana |
| Created Private Endpoint | ✅ `pe-test-grafana` connecting to PLS |
| Approved Connection | ✅ Manual approval workflow tested |
| Tested Connectivity | ✅ Can access Grafana via PE IP |

**Your Private Link Service is working!** 🎉

Consumers in other VNets/subscriptions can now create Private Endpoints using your alias and access Grafana privately without VNet peering.

---

**Document Owner**: DevOps/SRE Team  
**Last Updated**: October 14, 2025  
**Tested With**: AKS Observability Cluster, Grafana Service


