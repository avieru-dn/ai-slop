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

