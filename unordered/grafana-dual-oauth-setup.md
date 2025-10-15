# Grafana Dual OAuth Setup - Azure Entra ID + GitHub

This guide explains how to configure Grafana with **two simultaneous OAuth providers**: Azure Entra ID and GitHub.

## Overview

Grafana supports multiple OAuth providers running at the same time. Users will see both login options on the Grafana login page and can choose which provider to authenticate with.

## Prerequisites

### For Azure Entra ID
- Azure AD App Registration with:
  - Client ID: `b61c04d7-a6bf-41de-ae6a-f88587cdc800`
  - Client Secret: (already configured)
  - Tenant ID: `662f82da-cf45-4bdf-b295-33b083f5d229`
  - Redirect URI: `http://localhost:3000/login/azuread`

### For GitHub
- GitHub OAuth App with:
  - Client ID: (to be created)
  - Client Secret: (to be created)
  - Callback URL: `http://localhost:3000/login/github`

## Step 1: Create GitHub OAuth App

1. Go to **GitHub** → **Settings** → **Developer settings** → **OAuth Apps**
2. Click **"New OAuth App"**
3. Fill in the details:
   - **Application name**: `Grafana - DriveNets`
   - **Homepage URL**: `http://localhost:3000`
   - **Authorization callback URL**: `http://localhost:3000/login/github`
   - (For production, use: `https://grafana-local.dap.drivenets.com/login/github`)
4. Click **"Register application"**
5. Copy the **Client ID**
6. Click **"Generate a new client secret"**
7. Copy the **Client Secret** (you won't be able to see it again!)

## Step 2: Update the Kubernetes Secret

Update `grafana-simple.yaml` with your GitHub credentials:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: grafana-oauth-secrets
  namespace: grafana-test
type: Opaque
stringData:
  AZURE_CLIENT_SECRET: "YOUR_AZURE_CLIENT_SECRET_HERE"
  GITHUB_CLIENT_SECRET: "YOUR_GITHUB_CLIENT_SECRET_HERE"
```

## Step 3: Update GitHub Client ID in ConfigMap

Edit the `grafana.ini` section in `grafana-simple.yaml`:

```ini
[auth.github]
enabled = true
name = GitHub
client_id = YOUR_GITHUB_CLIENT_ID_HERE  # Replace this
```

## Step 4: Deploy to Kubernetes

```bash
# Deploy the updated configuration
kubectl apply -f grafana-simple.yaml

# Verify the deployment
kubectl get pods -n grafana-test
kubectl logs -n grafana-test -l app=grafana

# Port forward to access locally
kubectl port-forward -n grafana-test svc/grafana 3000:3000
```

## Step 5: Test Authentication

1. Open browser: `http://localhost:3000`
2. You should see **three login options**:
   - **Sign in with Azure Entra ID** (blue button)
   - **Sign in with GitHub** (black button)
   - **Username/Password** (admin/admin123)

### Test Azure Login
1. Click "Sign in with Azure Entra ID"
2. Authenticate with your `@drivenets.com` account
3. You should be logged in with **Viewer** role

### Test GitHub Login
1. Click "Sign in with GitHub"
2. Authenticate with your GitHub account
3. You should be logged in with **Viewer** role

## Configuration Details

### Azure Entra ID Settings
```ini
[auth.azuread]
enabled = true
name = Azure Entra ID
allow_sign_up = true
auto_login = false
scopes = openid email profile
allowed_domains = drivenets.com
```

**Key Features:**
- Only allows `@drivenets.com` email addresses
- No admin consent required (simplified setup)
- All users get Viewer role by default

### GitHub Settings
```ini
[auth.github]
enabled = true
name = GitHub
allow_sign_up = true
auto_login = false
scopes = user:email,read:org
allowed_organizations = drivenets
```

**Key Features:**
- Only allows members of the `drivenets` GitHub organization
- Requires `user:email` and `read:org` scopes
- All users get Viewer role by default

## Advanced: Role Mapping

### Azure Entra ID Role Mapping (Requires Admin Consent)

To enable group-based roles in Azure:

1. Update scopes to include `GroupMember.Read.All`:
```ini
scopes = openid email profile GroupMember.Read.All
```

2. Get Admin consent in Azure Portal
3. Get Azure AD Group Object IDs
4. Update role mapping:
```ini
skip_org_role_sync = false
role_attribute_path = contains(groups[*], 'ADMIN-GROUP-ID') && 'GrafanaAdmin' || contains(groups[*], 'EDITOR-GROUP-ID') && 'Editor' || 'Viewer'
```

### GitHub Team-Based Role Mapping

To enable team-based roles in GitHub:

1. Get your GitHub team IDs:
```bash
# Using GitHub API
curl -H "Authorization: token YOUR_GITHUB_TOKEN" \
  https://api.github.com/orgs/drivenets/teams
```

2. Update role mapping:
```ini
skip_org_role_sync = false
team_ids = 12345678,87654321
role_attribute_path = contains(teams[*].slug, 'admins') && 'GrafanaAdmin' || contains(teams[*].slug, 'editors') && 'Editor' || 'Viewer'
```

## User Experience

When users visit Grafana, they'll see:

```
┌─────────────────────────────────────┐
│         Welcome to Grafana          │
│                                     │
│  ┌─────────────────────────────┐  │
│  │  Sign in with Azure Entra ID │  │
│  └─────────────────────────────┘  │
│                                     │
│  ┌─────────────────────────────┐  │
│  │    Sign in with GitHub       │  │
│  └─────────────────────────────┘  │
│                                     │
│  ────────── Or ──────────          │
│                                     │
│  Username: [____________]          │
│  Password: [____________]          │
│  ┌─────────────────────────────┐  │
│  │        Log in               │  │
│  └─────────────────────────────┘  │
└─────────────────────────────────────┘
```

## Security Considerations

### ✅ Current Security Features
- Client secrets stored in Kubernetes Secrets (not ConfigMap)
- PKCE enabled for Azure AD
- Domain restrictions (`drivenets.com` for Azure)
- Organization restrictions (`drivenets` org for GitHub)
- Separate OAuth providers for different use cases

### 🔒 Recommended Enhancements
1. **Use Azure Key Vault** with CSI driver for secret management
2. **Rotate secrets regularly** (both Azure and GitHub support multiple secrets)
3. **Enable audit logging**:
```ini
[log.console]
level = info
format = json

[auditing]
enabled = true
```
4. **Use HTTPS in production** (update `root_url` and redirect URIs)
5. **Implement IP allowlists** if needed

## Troubleshooting

### Azure Login Issues

**Error: "AADSTS50011: The reply URL specified in the request does not match"**
- **Solution**: Update redirect URI in Azure App Registration to match exactly

**Error: "User authenticated but has no email"**
- **Solution**: Ensure `email` is in the scopes list

### GitHub Login Issues

**Error: "Organization membership required"**
- **Solution**: User must be a member of the `drivenets` GitHub organization
- Verify with: `https://github.com/orgs/drivenets/people`

**Error: "Application not authorized"**
- **Solution**: GitHub OAuth app may need organization approval
- Go to: GitHub Org Settings → OAuth App Access Restrictions

### General Issues

**Both providers show but login fails**
- Check Grafana logs:
```bash
kubectl logs -n grafana-test -l app=grafana | grep -i "oauth\|auth"
```

**Secrets not loading**
- Verify secret exists:
```bash
kubectl get secret grafana-oauth-secrets -n grafana-test -o yaml
```

## Production Deployment

For production environments:

1. **Update URLs**:
```ini
[server]
root_url = https://grafana-local.dap.drivenets.com

[auth.azuread]
# Update in Azure App Registration too
redirect_uri = https://grafana-local.dap.drivenets.com/login/azuread

[auth.github]
# Update in GitHub OAuth App too
callback_url = https://grafana-local.dap.drivenets.com/login/github
```

2. **Use Ingress with TLS**:
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: grafana
  namespace: grafana-test
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - grafana-local.dap.drivenets.com
    secretName: grafana-tls
  rules:
  - host: grafana-local.dap.drivenets.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: grafana
            port:
              number: 3000
```

3. **Enable Persistent Storage**:
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: grafana-storage
  namespace: grafana-test
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

## Reference Links

- [Grafana Azure AD OAuth Documentation](https://grafana.com/docs/grafana/latest/setup-grafana/configure-security/configure-authentication/azuread/)
- [Grafana GitHub OAuth Documentation](https://grafana.com/docs/grafana/latest/setup-grafana/configure-security/configure-authentication/github/)
- [GitHub OAuth Apps Documentation](https://docs.github.com/en/developers/apps/building-oauth-apps)
- [Azure AD App Registration Guide](https://learn.microsoft.com/en-us/azure/active-directory/develop/quickstart-register-app)

## Quick Commands Reference

```bash
# Deploy
kubectl apply -f grafana-simple.yaml

# Check status
kubectl get all -n grafana-test

# View logs
kubectl logs -n grafana-test -l app=grafana -f

# Port forward
kubectl port-forward -n grafana-test svc/grafana 3000:3000

# Delete and redeploy
kubectl delete -f grafana-simple.yaml
kubectl apply -f grafana-simple.yaml

# Get secret values (base64 decoded)
kubectl get secret grafana-oauth-secrets -n grafana-test -o jsonpath='{.data.GITHUB_CLIENT_SECRET}' | base64 -d

# Update secret
kubectl create secret generic grafana-oauth-secrets \
  --namespace=grafana-test \
  --from-literal=AZURE_CLIENT_SECRET="your-azure-secret" \
  --from-literal=GITHUB_CLIENT_SECRET="your-github-secret" \
  --dry-run=client -o yaml | kubectl apply -f -
```


