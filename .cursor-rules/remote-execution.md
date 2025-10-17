# Remote Execution Code Rule

## Triggers

When I prefix my request with:
- "RDP:"
- "REMOTE:"
- "execute remotely"
- "run on another machine"

## Response Format

Return ONLY executable code/commands without explanations:

- ✅ Code blocks with executable content
- ✅ Filename comments in code blocks
- ❌ No markdown explanations outside code blocks
- ❌ No conversational text
- ❌ No additional context or warnings

## Code Structure

### Bash/Linux Scripts
```bash
# filename: script_name.sh
#!/usr/bin/env bash
set -euo pipefail

# Your code here
```

### PowerShell/Windows Scripts
```powershell
# filename: script_name.ps1
[CmdletBinding()]
param()

# Your code here
```

### Configuration Files
```yaml
# filename: config.yaml
key: value
```

## Multi-File Operations

Separate each file clearly:

```bash
# filename: setup.sh
#!/usr/bin/env bash
echo "Setting up..."
```

```bash
# filename: deploy.sh
#!/usr/bin/env bash
echo "Deploying..."
```

## Safety Requirements

- Code should be production-ready
- No destructive operations without confirmation flags
- Include error handling where critical
- Assume standard tools are available unless specified
- Use environment variables for sensitive data

## Examples

**Request:** "REMOTE: Install Docker on Ubuntu"

**Response:**
```bash
# filename: install_docker.sh
#!/usr/bin/env bash
set -euo pipefail

sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
```

