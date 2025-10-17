# Git Commit Message Standards

## Conventional Commits Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

## Types

### Primary Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, missing semicolons, etc.)
- `refactor`: Code refactoring (neither fixes a bug nor adds a feature)
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks (dependencies, build config, etc.)
- `ci`: CI/CD pipeline changes
- `build`: Build system changes

## Rules

### Subject Line
- Keep under 50 characters
- Use imperative mood ("Add feature" not "Added feature" or "Adds feature")
- Don't end with a period
- Capitalize first letter
- Be specific and concise

### Body (Optional)
- Wrap at 72 characters
- Explain **what** and **why**, not **how**
- Separate from subject with blank line
- Use bullet points for multiple items

### Footer (Optional)
- Reference issues: `Fixes #123`, `Closes #456`
- Breaking changes: `BREAKING CHANGE: description`
- Co-authors: `Co-authored-by: Name <email>`

## Examples

### Feature Addition
```
feat(exporter): add Azure blob storage metrics support

- Implement blob count metric
- Add storage capacity metric
- Include last modified timestamp

This enables monitoring of blob storage usage across
multiple storage accounts.

Closes #45
```

### Bug Fix
```
fix(k8s): correct service monitor selector labels

The service monitor was using incorrect label selectors,
preventing Prometheus from discovering the exporter.

Fixed by updating matchLabels to use app.kubernetes.io/name
instead of the deprecated app label.

Fixes #123
```

### Documentation
```
docs(readme): update installation instructions

- Add prerequisites section
- Include Azure CLI setup steps
- Add troubleshooting guide
- Update example commands
```

### Refactoring
```
refactor(metrics): extract collector logic into separate class

Moved metric collection logic from main file into
dedicated MetricsCollector class to improve code
organization and testability.

No functional changes.
```

### Performance
```
perf(cache): implement Redis caching for API responses

Added Redis-based caching layer to reduce Azure API calls
by 80%. Cache TTL is configurable via CACHE_TTL env var.

Reduces scrape time from 30s to 3s for typical workloads.
```

### Chore
```
chore(deps): bump prometheus-client to 0.19.0

Updated prometheus-client library to latest version for
security patches and bug fixes.
```

### CI/CD
```
ci(pipeline): add automated docker image build

- Build Docker image on every push to main
- Tag with git commit SHA and 'latest'
- Push to Azure Container Registry
- Run security scan with Trivy
```

### Breaking Change
```
feat(api)!: change metric label from 'account' to 'storage_account'

Updated metric label names to follow Prometheus naming
conventions and improve clarity.

BREAKING CHANGE: Existing dashboards and alerts using
the 'account' label will need to be updated to use
'storage_account' instead.

Migration guide:
- Update Prometheus queries: account -> storage_account
- Update Grafana dashboards
- Update alert rules

Refs #234
```

### Multiple Issues
```
fix(deployment): resolve multiple deployment issues

- Fix namespace creation order (#123)
- Correct RBAC permissions (#124)
- Update service account reference (#125)

These fixes ensure the Kubernetes manifests deploy
correctly in all environments.

Fixes #123, #124, #125
```

### Co-authored Commit
```
feat(monitoring): add custom Grafana dashboard

Created comprehensive dashboard with:
- Storage capacity metrics
- Blob count trends
- Cost analysis panels
- Alert status indicators

Co-authored-by: Jane Doe <jane@example.com>
Co-authored-by: John Smith <john@example.com>

Closes #78
```

## Scope Examples

### By Component
- `exporter`: Azure storage exporter
- `k8s`: Kubernetes manifests
- `dashboard`: Grafana dashboard
- `pipeline`: CI/CD pipeline
- `docs`: Documentation
- `tests`: Test suite
- `deps`: Dependencies

### By File/Module
- `deployment`: Kubernetes deployment
- `service`: Kubernetes service
- `metrics`: Metrics collection
- `cache`: Caching layer
- `api`: API interactions

## Bad Examples

### Too Vague
```
❌ fix: fixed bug
❌ update: updated files
❌ chore: changes
```

### Not Imperative
```
❌ feat: added new feature
❌ fix: fixing the bug
❌ docs: updated readme
```

### Too Long Subject
```
❌ feat: implement comprehensive Azure storage account metrics 
   collection with support for multiple subscriptions and resource groups
```

### No Type
```
❌ Fixed the bug in deployment
❌ Updated readme
```

## Good Examples

### Simple Fix
```
✅ fix(deployment): correct service port number

Changed port from 8080 to 9090 to match exporter default.

Fixes #45
```

### Feature with Context
```
✅ feat(metrics): add snapshot count metric

Implemented azure_storage_snapshot_count metric to track
the number of snapshots per blob container.

This metric helps monitor snapshot growth and manage
storage costs.

Closes #67
```

### Documentation Update
```
✅ docs(guide): add scrape interval optimization guide

Created SCRAPE_INTERVAL_GUIDE.md with:
- Performance considerations
- Cost optimization tips
- Recommended intervals by use case
```

### Dependency Update
```
✅ chore(deps): bump azure-storage-blob to 12.19.0

Security update addressing CVE-2024-12345.
```

### Quick Fix
```
✅ fix(typo): correct variable name in deployment

Changed DATABSE_URL to DATABASE_URL.

Fixes #89
```

## Commit Frequency

### When to Commit
- After completing a logical unit of work
- Before switching tasks or contexts
- After fixing a bug (one fix per commit)
- After adding a feature (one feature per commit)
- Before end of day (if work is in progress)

### Avoid
- Committing broken code to main/master
- Combining unrelated changes
- Committing generated files (build artifacts, logs)
- Committing secrets or credentials
- Making huge commits (prefer small, focused commits)

## Branch Naming

```
<type>/<short-description>

Examples:
- feature/azure-metrics
- fix/service-monitor-labels
- docs/installation-guide
- refactor/metrics-collector
- hotfix/deployment-port
```

## Rewriting History

```bash
# Amend last commit message
git commit --amend

# Interactive rebase to edit multiple commits
git rebase -i HEAD~3

# Squash commits before merging
git rebase -i main
```

**Note:** Never rewrite history on shared branches (main, master, develop).

## Tools

### Commitlint
```javascript
// .commitlintrc.js
module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [
      2,
      'always',
      [
        'feat',
        'fix',
        'docs',
        'style',
        'refactor',
        'perf',
        'test',
        'chore',
        'ci',
        'build'
      ]
    ],
    'subject-max-length': [2, 'always', 50],
    'body-max-line-length': [2, 'always', 72]
  }
};
```

### Pre-commit Hook
```bash
#!/bin/bash
# .git/hooks/commit-msg

commit_msg_file=$1
commit_msg=$(cat "$commit_msg_file")

# Check conventional commit format
if ! echo "$commit_msg" | grep -qE '^(feat|fix|docs|style|refactor|perf|test|chore|ci|build)(\(.+\))?: .+'; then
    echo "ERROR: Commit message doesn't follow conventional commits format"
    echo "Expected: <type>(<scope>): <subject>"
    exit 1
fi

# Check subject length
subject=$(echo "$commit_msg" | head -n1)
if [ ${#subject} -gt 50 ]; then
    echo "ERROR: Subject line exceeds 50 characters (${#subject})"
    exit 1
fi
```

## Checklist

- ✅ Follows conventional commits format
- ✅ Type is appropriate
- ✅ Subject under 50 characters
- ✅ Uses imperative mood
- ✅ Subject doesn't end with period
- ✅ Body explains what and why (if needed)
- ✅ Body lines wrapped at 72 characters
- ✅ References related issues
- ✅ Includes breaking change notice if applicable
- ✅ One logical change per commit

