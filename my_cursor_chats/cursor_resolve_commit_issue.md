# Resolve commit issue
_Exported on 17/10/2025 at 11:59:52 EEST from Cursor (1.7.46)_

---

**User**

solve this commit

---

**Cursor**

I'll help you with the commit. Let me first check the current git status to see what needs to be committed.

The git status shows that there are no changes to commit - the working tree is clean. This means either:

1. All changes have already been committed
2. There are no modified files
3. You might be referring to something else

Could you clarify what you'd like me to help you with? For example:
- Do you have uncommitted changes that aren't showing up?
- Do you want to create a new commit with specific changes?
- Are you trying to resolve a commit issue (like amending, rebasing, or fixing a merge conflict)?
- Do you want me to check if there are any untracked files that should be added?

Let me also check if there are any untracked files:

---

**User**

cannot push to github 

---

**Cursor**

Let me check the current git status and see what's preventing you from pushing to GitHub.

Now let me try to push and see what error you're encountering:

I found the issue! GitHub's push protection detected **Azure Active Directory Application Secrets** in several files from commit `cf391a8`. The secrets are located in:

1. `unordered/github-oauth-app-creation.md` (lines 52 and 198)
2. `unordered/grafana-dual-oauth-setup.md` (line 50)
3. `unordered/grafana-simple.yaml` (line 13)
4. `unordered/values-dev.yaml` (line 16)

Let me check these files to identify and remove the secrets:

Perfect! I found the Azure AD secrets that need to be removed. The secret `[REDACTED_AZURE_SECRET]` appears in multiple files. I'll create a todo list and then fix all the occurrences by replacing them with placeholder text.

```markdown
# Creating GitHub OAuth App for Grafana

## Step-by-Step Guide

### 1. Navigate to GitHub OAuth Apps
1. Go to **https://github.com/settings/developers**
2. Or: GitHub (top right) → **Settings** → **Developer settings** (left sidebar) → **OAuth Apps**

### 2. Create New OAuth App
1. Click **"New OAuth App"** button
2. Fill in the form:

```
Application name: Grafana - DriveNets
Homepage URL: http://localhost:3000
Application description: Grafana authentication for DriveNets team
Authorization callback URL: http://localhost:3000/login/github
```

**Important:** The callback URL must be exact:
- For local testing: `http://localhost:3000/login/github`
- For production: `https://grafana-local.dap.drivenets.com/login/github`

3. Click **"Register application"**

### 3. Get Your Credentials

After creating the app, you'll see:

#### Client ID
```
Example: Iv1.a629723d4f5e6789
```
- This is **public** and can be stored in ConfigMap
- Copy this value

#### Client Secret
1. Click **"Generate a new client secret"**
2. You'll see something like:
```
Example: gho_16C7e42F292c6912E7710c838347Ae178B4a
```
- This is **secret** and should be stored in Kubernetes Secret
- Copy this immediately - you won't see it again!
- If you lose it, you'll need to regenerate a new one

### 4. Update Your Grafana Configuration

#### Update the Secret (line 14):
```yaml
stringData:
  AZURE_CLIENT_SECRET: "YOUR_AZURE_CLIENT_SECRET_HERE"
  GITHUB_CLIENT_SECRET: "gho_YOUR_ACTUAL_CLIENT_SECRET_HERE"  # Paste here
```

#### Update the ConfigMap (line 60):
```yaml
[auth.github]
enabled = true
name = GitHub
allow_sign_up = true
auto_login = false
client_id = Iv1.YOUR_ACTUAL_CLIENT_ID_HERE  # Paste here
client_secret = $__env{GITHUB_CLIENT_SECRET}
```

### 5. Optional: Configure for Organization

If you want to restrict to `drivenets` organization members:

1. **Organization Approval (if needed)**:
   - Go to: https://github.com/organizations/drivenets/settings/oauth_application_policy
   - You may need to request approval from org admins
   - Or remove the `allowed_organizations` line from config

2. **Test Organization Membership**:
   ```bash
   # Check if you're a member
   curl -H "Authorization: token YOUR_PERSONAL_TOKEN" \
     https://api.github.com/orgs/drivenets/members/YOUR_USERNAME
   ```

### 6. Deploy and Test

```bash
# Apply the updated configuration
kubectl apply -f grafana-simple.yaml

# Check if it's running
kubectl get pods -n grafana-test

# Port forward
kubectl port-forward -n grafana-test svc/grafana 3000:3000

# Open browser
open http://localhost:3000
```

## Quick Reference

### What Goes Where?

| Item | Type | Where to Put It | Public/Secret |
|------|------|----------------|---------------|
| Azure Client ID | UUID format | Deployment env var | Can be public |
| Azure Client Secret | Long string | Kubernetes Secret | **SECRET** |
| Azure Tenant ID | UUID format | Kubernetes Secret | Can be public |
| GitHub Client ID | `Iv1.xxxxxxxx` | ConfigMap | Can be public |
| GitHub Client Secret | `gho_xxxxxxxx` | Kubernetes Secret | **SECRET** |
| Admin Password | Any string | Kubernetes Secret | **SECRET** |

### Common Mistakes

❌ **Wrong:** Using Personal Access Token as Client Secret
```yaml
GITHUB_CLIENT_SECRET: "ghp_xxxxxxxxxxxxxxxxxxxx"  # This won't work!
```

✅ **Correct:** Using OAuth Client Secret
```yaml
GITHUB_CLIENT_SECRET: "gho_xxxxxxxxxxxxxxxxxxxx"  # This works!
```

❌ **Wrong:** Using wrong callback URL
```
Callback: https://grafana-local.dap.drivenets.com/oauth/callback  # Wrong!
```

✅ **Correct:** GitHub OAuth specific path
```
Callback: https://grafana-local.dap.drivenets.com/login/github  # Correct!
```

## Troubleshooting

### Error: "The redirect_uri MUST match the registered callback URL"
**Solution:** 
- Go back to your GitHub OAuth App settings
- Update the Authorization callback URL to exactly match what Grafana is using
- It's case-sensitive and must include the `/login/github` path

### Error: "Bad credentials"
**Solution:**
- Regenerate a new Client Secret in GitHub
- Update the Kubernetes Secret
- Restart Grafana pod: `kubectl rollout restart deployment/grafana -n grafana-test`

### Can't Find the OAuth App
**Options:**
1. Personal OAuth App: https://github.com/settings/developers
2. Organization OAuth App: https://github.com/organizations/drivenets/settings/applications

### Need to Regenerate Secret?
1. Go to your OAuth App settings
2. Click "Generate a new client secret"
3. The old one will still work until you delete it
4. This allows zero-downtime rotation!

## Security Best Practices

1. **Never commit secrets to Git**
   ```bash
   # Check before committing
   git diff grafana-simple.yaml | grep -i secret
   ```

2. **Use different apps for different environments**
   - `Grafana Dev - DriveNets` for testing
   - `Grafana Prod - DriveNets` for production

3. **Rotate secrets regularly**
   - GitHub supports 2 active secrets simultaneously
   - Generate new → Update Kubernetes → Delete old

4. **Restrict to organization**
   ```yaml
   allowed_organizations = drivenets
   ```

5. **Use specific scopes only**
   ```yaml
   scopes = user:email,read:org  # Minimal required permissions
   ```

## Example: Complete Configuration

Once you have both Client ID and Client Secret:

```yaml
---
apiVersion: v1
kind: Secret
metadata:
  name: grafana-oauth-secrets
  namespace: grafana-test
type: Opaque
stringData:
  AZURE_CLIENT_SECRET: "YOUR_AZURE_CLIENT_SECRET_HERE"
  GITHUB_CLIENT_SECRET: "YOUR_GITHUB_CLIENT_SECRET_HERE"  # Your actual secret
---
# In ConfigMap grafana.ini section:
[auth.github]
enabled = true
name = GitHub
allow_sign_up = true
auto_login = false
client_id = Iv1.a629723d4f5e6789  # Your actual client ID
client_secret = $__env{GITHUB_CLIENT_SECRET}
scopes = user:email,read:org
auth_url = https://github.com/login/oauth/authorize
token_url = https://github.com/login/oauth/access_token
api_url = https://api.github.com/user
allowed_organizations = drivenets
```

## Need Help?

If you're stuck:
1. Check Grafana logs: `kubectl logs -n grafana-test -l app=grafana | grep -i github`
2. Verify secret exists: `kubectl get secret grafana-oauth-secrets -n grafana-test`
3. Test the OAuth flow manually at: http://localhost:3000

## Next Steps After Setup

1. ✅ Create GitHub OAuth App
2. ✅ Get Client ID and Client Secret
3. ✅ Update grafana-simple.yaml
4. ✅ Deploy to Kubernetes
5. ✅ Test login with both Azure and GitHub
6. 🔄 Set up team-based role mapping (optional)
7. 🔄 Move to production with HTTPS (optional)


```

```markdown
# Creating GitHub OAuth App for Grafana

## Step-by-Step Guide

### 1. Navigate to GitHub OAuth Apps
1. Go to **https://github.com/settings/developers**
2. Or: GitHub (top right) → **Settings** → **Developer settings** (left sidebar) → **OAuth Apps**

### 2. Create New OAuth App
1. Click **"New OAuth App"** button
2. Fill in the form:

```
Application name: Grafana - DriveNets
Homepage URL: http://localhost:3000
Application description: Grafana authentication for DriveNets team
Authorization callback URL: http://localhost:3000/login/github
```

**Important:** The callback URL must be exact:
- For local testing: `http://localhost:3000/login/github`
- For production: `https://grafana-local.dap.drivenets.com/login/github`

3. Click **"Register application"**

### 3. Get Your Credentials

After creating the app, you'll see:

#### Client ID
```
Example: Iv1.a629723d4f5e6789
```
- This is **public** and can be stored in ConfigMap
- Copy this value

#### Client Secret
1. Click **"Generate a new client secret"**
2. You'll see something like:
```
Example: gho_16C7e42F292c6912E7710c838347Ae178B4a
```
- This is **secret** and should be stored in Kubernetes Secret
- Copy this immediately - you won't see it again!
- If you lose it, you'll need to regenerate a new one

### 4. Update Your Grafana Configuration

#### Update the Secret (line 14):
```yaml
stringData:
  AZURE_CLIENT_SECRET: "YOUR_AZURE_CLIENT_SECRET_HERE"
  GITHUB_CLIENT_SECRET: "gho_YOUR_ACTUAL_CLIENT_SECRET_HERE"  # Paste here
```

#### Update the ConfigMap (line 60):
```yaml
[auth.github]
enabled = true
name = GitHub
allow_sign_up = true
auto_login = false
client_id = Iv1.YOUR_ACTUAL_CLIENT_ID_HERE  # Paste here
client_secret = $__env{GITHUB_CLIENT_SECRET}
```

### 5. Optional: Configure for Organization

If you want to restrict to `drivenets` organization members:

1. **Organization Approval (if needed)**:
   - Go to: https://github.com/organizations/drivenets/settings/oauth_application_policy
   - You may need to request approval from org admins
   - Or remove the `allowed_organizations` line from config

2. **Test Organization Membership**:
   ```bash
   # Check if you're a member
   curl -H "Authorization: token YOUR_PERSONAL_TOKEN" \
     https://api.github.com/orgs/drivenets/members/YOUR_USERNAME
   ```

### 6. Deploy and Test

```bash
# Apply the updated configuration
kubectl apply -f grafana-simple.yaml

# Check if it's running
kubectl get pods -n grafana-test

# Port forward
kubectl port-forward -n grafana-test svc/grafana 3000:3000

# Open browser
open http://localhost:3000
```

## Quick Reference

### What Goes Where?

| Item | Type | Where to Put It | Public/Secret |
|------|------|----------------|---------------|
| Azure Client ID | UUID format | Deployment env var | Can be public |
| Azure Client Secret | Long string | Kubernetes Secret | **SECRET** |
| Azure Tenant ID | UUID format | Kubernetes Secret | Can be public |
| GitHub Client ID | `Iv1.xxxxxxxx` | ConfigMap | Can be public |
| GitHub Client Secret | `gho_xxxxxxxx` | Kubernetes Secret | **SECRET** |
| Admin Password | Any string | Kubernetes Secret | **SECRET** |

### Common Mistakes

❌ **Wrong:** Using Personal Access Token as Client Secret
```yaml
GITHUB_CLIENT_SECRET: "ghp_xxxxxxxxxxxxxxxxxxxx"  # This won't work!
```

✅ **Correct:** Using OAuth Client Secret
```yaml
GITHUB_CLIENT_SECRET: "gho_xxxxxxxxxxxxxxxxxxxx"  # This works!
```

❌ **Wrong:** Using wrong callback URL
```
Callback: https://grafana-local.dap.drivenets.com/oauth/callback  # Wrong!
```

✅ **Correct:** GitHub OAuth specific path
```
Callback: https://grafana-local.dap.drivenets.com/login/github  # Correct!
```

## Troubleshooting

### Error: "The redirect_uri MUST match the registered callback URL"
**Solution:** 
- Go back to your GitHub OAuth App settings
- Update the Authorization callback URL to exactly match what Grafana is using
- It's case-sensitive and must include the `/login/github` path

### Error: "Bad credentials"
**Solution:**
- Regenerate a new Client Secret in GitHub
- Update the Kubernetes Secret
- Restart Grafana pod: `kubectl rollout restart deployment/grafana -n grafana-test`

### Can't Find the OAuth App
**Options:**
1. Personal OAuth App: https://github.com/settings/developers
2. Organization OAuth App: https://github.com/organizations/drivenets/settings/applications

### Need to Regenerate Secret?
1. Go to your OAuth App settings
2. Click "Generate a new client secret"
3. The old one will still work until you delete it
4. This allows zero-downtime rotation!

## Security Best Practices

1. **Never commit secrets to Git**
   ```bash
   # Check before committing
   git diff grafana-simple.yaml | grep -i secret
   ```

2. **Use different apps for different environments**
   - `Grafana Dev - DriveNets` for testing
   - `Grafana Prod - DriveNets` for production

3. **Rotate secrets regularly**
   - GitHub supports 2 active secrets simultaneously
   - Generate new → Update Kubernetes → Delete old

4. **Restrict to organization**
   ```yaml
   allowed_organizations = drivenets
   ```

5. **Use specific scopes only**
   ```yaml
   scopes = user:email,read:org  # Minimal required permissions
   ```

## Example: Complete Configuration

Once you have both Client ID and Client Secret:

```yaml
---
apiVersion: v1
kind: Secret
metadata:
  name: grafana-oauth-secrets
  namespace: grafana-test
type: Opaque
stringData:
  AZURE_CLIENT_SECRET: "YOUR_AZURE_CLIENT_SECRET_HERE"
  GITHUB_CLIENT_SECRET: "YOUR_GITHUB_CLIENT_SECRET_HERE"  # Your actual secret
---
# In ConfigMap grafana.ini section:
[auth.github]
enabled = true
name = GitHub
allow_sign_up = true
auto_login = false
client_id = Iv1.a629723d4f5e6789  # Your actual client ID
client_secret = $__env{GITHUB_CLIENT_SECRET}
scopes = user:email,read:org
auth_url = https://github.com/login/oauth/authorize
token_url = https://github.com/login/oauth/access_token
api_url = https://api.github.com/user
allowed_organizations = drivenets
```

## Need Help?

If you're stuck:
1. Check Grafana logs: `kubectl logs -n grafana-test -l app=grafana | grep -i github`
2. Verify secret exists: `kubectl get secret grafana-oauth-secrets -n grafana-test`
3. Test the OAuth flow manually at: http://localhost:3000

## Next Steps After Setup

1. ✅ Create GitHub OAuth App
2. ✅ Get Client ID and Client Secret
3. ✅ Update grafana-simple.yaml
4. ✅ Deploy to Kubernetes
5. ✅ Test login with both Azure and GitHub
6. 🔄 Set up team-based role mapping (optional)
7. 🔄 Move to production with HTTPS (optional)


```

```markdown
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



```

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: grafana-test
---
apiVersion: v1
kind: Secret
metadata:
  name: grafana-oauth-secrets
  namespace: grafana-test
type: Opaque
stringData:
  AZURE_CLIENT_SECRET: "YOUR_AZURE_CLIENT_SECRET_HERE"
  GITHUB_CLIENT_SECRET: "YOUR_GITHUB_CLIENT_SECRET_HERE"
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-config
  namespace: grafana-test
data:
  grafana.ini: |
    [server]
    root_url = http://localhost:3000
    serve_from_sub_path = false
    http_port = 3000
    
    [security]
    admin_user = admin
    admin_password = admin123
    disable_gravatar = true
    
    # Azure Entra ID OAuth Configuration
    [auth.azuread]
    enabled = true
    name = Azure Entra ID
    allow_sign_up = true
    auto_login = false
    client_id = b61c04d7-a6bf-41de-ae6a-f88587cdc800
    client_secret = $__env{AZURE_CLIENT_SECRET}
    scopes = openid email profile
    auth_url = https://login.microsoftonline.com/662f82da-cf45-4bdf-b295-33b083f5d229/oauth2/v2.0/authorize
    token_url = https://login.microsoftonline.com/662f82da-cf45-4bdf-b295-33b083f5d229/oauth2/v2.0/token
    api_url = https://graph.microsoft.com/v1.0/me
    use_pkce = true
    allow_assign_grafana_admin = false
    skip_org_role_sync = true
    role_attribute_strict = false
    allowed_domains = drivenets.com
    # Role mapping disabled - no admin consent required
    # All users will get the default role set in [users] section below
    # To enable group-based roles: add 'GroupMember.Read.All' to scopes and get admin consent
    
    # GitHub OAuth Configuration
    [auth.github]
    enabled = true
    name = GitHub
    allow_sign_up = true
    auto_login = false
    client_id = Ov23liUFQMIDwm6Ara2F
    client_secret = $__env{GITHUB_CLIENT_SECRET}
    scopes = user:email,read:org
    auth_url = https://github.com/login/oauth/authorize
    token_url = https://github.com/login/oauth/access_token
    api_url = https://api.github.com/user
    # allowed_organizations = drivenets  # Commented out - allow any GitHub user
    allow_assign_grafana_admin = false

    
    skip_org_role_sync = true
    # Team-based role mapping (optional):
    # team_ids = 12345678
    # role_attribute_path = contains(teams[*].slug, 'admins') && 'GrafanaAdmin' || contains(teams[*].slug, 'editors') && 'Editor' || 'Viewer'
    
    [users]
    auto_assign_org = true
    auto_assign_org_role = Viewer
    
    [log]
    mode = console
    level = info
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grafana
  namespace: grafana-test
spec:
  replicas: 1
  selector:
    matchLabels:
      app: grafana
  template:
    metadata:
      labels:
        app: grafana
    spec:
      containers:
      - name: grafana
        image: grafana/grafana:latest
        ports:
        - containerPort: 3000
        env:
        - name: AZURE_CLIENT_SECRET
          valueFrom:
            secretKeyRef:
              name: grafana-oauth-secrets
              key: AZURE_CLIENT_SECRET
        - name: GITHUB_CLIENT_SECRET
          valueFrom:
            secretKeyRef:
              name: grafana-oauth-secrets
              key: GITHUB_CLIENT_SECRET
        volumeMounts:
        - name: grafana-config
          mountPath: /etc/grafana/grafana.ini
          subPath: grafana.ini
      volumes:
      - name: grafana-config
        configMap:
          name: grafana-config
---
apiVersion: v1
kind: Service
metadata:
  name: grafana
  namespace: grafana-test
spec:
  selector:
    app: grafana
  ports:
  - port: 3000
    targetPort: 3000
  type: ClusterIP

```

```yaml
# Development environment values
# Override values.yaml for local development

namespace:
  create: true
  name: grafana-test

grafana:
  server:
    rootUrl: http://localhost:3000

oauth:
  azuread:
    enabled: true
    clientId: "b61c04d7-a6bf-41de-ae6a-f88587cdc800"
    clientSecret: "YOUR_AZURE_CLIENT_SECRET_HERE"
    tenantId: "662f82da-cf45-4bdf-b295-33b083f5d229"
  
  github:
    enabled: true
    clientId: "Ov23liUFQMIDwm6Ara2F"
    clientSecret: "YOUR_GITHUB_CLIENT_SECRET"
    # allowedOrganizations: "drivenets"  # Commented out for testing

persistence:
  enabled: false

ingress:
  enabled: false



```

Great! All secrets have been replaced. Now I need to update the TODO list and amend the commit to remove the secrets from git history:

Perfect! Now I need to stage these changes and amend the commit that contains the secrets. Since the secrets were introduced in commit `cf391a8`, I'll need to amend that specific commit:

Good! The files are staged. Now I need to use an interactive rebase to edit commit `cf391a8` and remove the secrets. Let me do this:

I need to commit the changes first as part of a fixup commit, then do an interactive rebase. Let me use a different approach - I'll create a fixup commit and then rebase:

Now I'll use an interactive rebase with autosquash to merge the fixup commit into the original commit:

Excellent! The rebase was successful. Let me verify the git log to confirm the secrets have been removed from the commit history:

I see the autosquash didn't work as expected. Let me try a different approach using a manual interactive rebase:

Good! Now let me commit these changes with the secrets already removed:

I see there's still the old commit `cf391a8` in the history. Let me check what's in that commit and remove it properly:

I see the issue - commit `cf391a8` contains the files with secrets, and my new commit `15624a6` also contains them. I need to rebase to remove the old commit `cf391a8` entirely since the new commit already contains all the files (with secrets removed). Let me do an interactive rebase:

Perfect! Let me verify that the commit with secrets has been removed:

I see the issue - the problematic commit `cf391a8` is still there, and it still contains the secrets. Let me check what happened:

It looks like my last rebase removed the wrong commit. Let me check the current state and fix this properly:

I see - my rebase removed the wrong commit. Let me recover the good commit and properly fix this. I'll use git reflog to go back to commit `15624a6` which had all the files with secrets removed:

Good! Now I need to remove commit `cf391a8` which contains the secrets. Let me use an interactive rebase to drop that commit:

Perfect! There are conflicts because we're modifying files that were added in the commit we're removing. I need to add these files since we want to keep them (with secrets removed):

Excellent! The rebase was successful. Now let me verify that the secrets have been removed from the git history:

Perfect! The commit with secrets (`cf391a8`) has been successfully removed from the git history, and the current commit (`e4b7791`) now contains the files with placeholder values instead of actual secrets. Let me verify all the affected files:

Excellent! All secrets have been successfully replaced with placeholders. Now let me update the TODO list and attempt to push to GitHub:

Perfect! The push was successful! Let me update the TODO list to mark everything as completed:

## ✅ Successfully Resolved!

I've successfully resolved the GitHub push protection issue. Here's what was done:

### Problem
GitHub's push protection detected **Azure Active Directory Application Secrets** in commit `cf391a8` across multiple files:
- `unordered/github-oauth-app-creation.md` (2 locations)
- `unordered/grafana-dual-oauth-setup.md`
- `unordered/grafana-simple.yaml`
- `unordered/values-dev.yaml`

### Solution
1. **Replaced all secrets** with placeholder text (`YOUR_AZURE_CLIENT_SECRET_HERE`, `YOUR_GITHUB_CLIENT_SECRET_HERE`)
2. **Rewrote git history** using interactive rebase to remove the commit containing secrets
3. **Successfully pushed** the cleaned commit history to GitHub

### Current State
- Git history is now clean with only 2 commits:
  - `e4b7791` - Add metric for last Azure API fetch duration and unordered files (with secrets removed)
  - `29a300e` - Initial commit - Azure Storage Exporter
- All secrets have been replaced with placeholders
- Changes have been successfully pushed to GitHub

**Important:** Since these secrets were exposed in your git history, you should **revoke and regenerate** them in Azure to ensure security:
1. Go to Azure Portal → Azure Active Directory → App registrations
2. Find your application and regenerate the client secret
3. Update your local configuration with the new secret (but don't commit it!)

