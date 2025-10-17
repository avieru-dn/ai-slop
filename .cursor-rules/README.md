# Cursor Rules Directory

This directory contains detailed rule sets for use with Cursor AI assistant. Each file can be referenced using the `@` symbol in Cursor.

## Available Rules

### 📝 [english-enhancement.md](./english-enhancement.md)
Grammar correction and writing improvement guidelines. Use when you need help with:
- Correcting grammatical errors
- Improving sentence structure
- Finding better phrasings
- Professional writing

**Usage in Cursor:** `@english-enhancement.md` + your text

---

### 🖥️ [remote-execution.md](./remote-execution.md)
Code-only output for remote execution. Returns executable scripts without explanations.

**Triggers:**
- Prefix requests with "RDP:", "REMOTE:", or "execute remotely"

**Usage in Cursor:** `@remote-execution.md` + "RDP: install docker on ubuntu"

---

### 🔧 [devops-principles.md](./devops-principles.md)
Core DevOps principles and best practices including:
- Automation and IaC
- Security and least privilege
- Error handling and logging
- Cost optimization

**Usage in Cursor:** `@devops-principles.md`

---

### ☁️ [azure-best-practices.md](./azure-best-practices.md)
Azure-specific guidelines covering:
- Managed identities and authentication
- Resource naming and tagging
- Networking and security
- Monitoring and cost management

**Usage in Cursor:** `@azure-best-practices.md`

---

### ⚓ [kubernetes-standards.md](./kubernetes-standards.md)
Kubernetes manifest standards including:
- Resource definitions
- Security contexts
- Health checks and probes
- Autoscaling and RBAC

**Usage in Cursor:** `@kubernetes-standards.md`

---

### 🐍 [python-standards.md](./python-standards.md)
Python coding standards covering:
- Type hints and docstrings
- Error handling
- Logging setup
- Testing with pytest

**Usage in Cursor:** `@python-standards.md`

---

### 📜 [bash-scripting.md](./bash-scripting.md)
Bash scripting best practices including:
- Script templates
- Error handling
- Input validation
- Security practices

**Usage in Cursor:** `@bash-scripting.md`

---

### 🤖 [ansible-standards.md](./ansible-standards.md)
Ansible playbook standards covering:
- Idempotent task design
- Role organization
- Variable management
- Vault for secrets

**Usage in Cursor:** `@ansible-standards.md`

---

### 📋 [git-commit-messages.md](./git-commit-messages.md)
Conventional commits format and guidelines including:
- Commit types and scopes
- Subject line rules
- Examples and anti-patterns

**Usage in Cursor:** `@git-commit-messages.md`

---

## How to Use

### In Cursor Chat

1. **Reference a specific rule:**
   ```
   @kubernetes-standards.md help me write a deployment
   ```

2. **Combine multiple rules:**
   ```
   @python-standards.md @bash-scripting.md create a deployment script
   ```

3. **English improvement:**
   ```
   @english-enhancement.md 
   Please check: "The system are running slow and need optimization"
   ```

4. **Remote execution:**
   ```
   @remote-execution.md
   RDP: Install PostgreSQL 14 on Ubuntu 22.04
   ```

### Quick Reference

| Task | Command |
|------|---------|
| Fix grammar | `@english-enhancement.md` + your text |
| Remote script | `@remote-execution.md RDP:` + task |
| K8s manifest | `@kubernetes-standards.md` + request |
| Python code | `@python-standards.md` + request |
| Bash script | `@bash-scripting.md` + request |
| Ansible playbook | `@ansible-standards.md` + request |
| Azure resource | `@azure-best-practices.md` + request |
| Commit message | `@git-commit-messages.md` + changes |

## Rule Categories

### 📚 Language & Writing
- english-enhancement.md

### 💻 Programming Languages
- python-standards.md
- bash-scripting.md

### 🏗️ Infrastructure & Cloud
- devops-principles.md
- azure-best-practices.md
- kubernetes-standards.md
- ansible-standards.md

### 🔨 Development Workflow
- git-commit-messages.md
- remote-execution.md

## Tips

1. **Combine rules** for complex tasks that span multiple domains
2. **Reference before asking** to get responses that follow standards
3. **Use remote-execution** when you need copy-paste ready code
4. **Check english-enhancement** for all documentation and README updates

## Maintenance

These rules are version controlled and should be updated as:
- Tools and best practices evolve
- Team standards change
- New patterns emerge
- Feedback is received

## Contributing

To add or update rules:

1. Create or modify the markdown file in `.cursor-rules/`
2. Update this README.md with the new rule
3. Follow the existing format and structure
4. Add examples and use cases
5. Test with Cursor before committing

---

**Last Updated:** 2025-01-17  
**Maintained by:** DevOps Team

