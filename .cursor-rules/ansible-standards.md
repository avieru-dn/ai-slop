# Ansible Standards and Best Practices

## Playbook Structure

### Basic Playbook Template
```yaml
---
# playbook.yml
# Description: Deploy web application
# Author: DevOps Team
# Date: 2025-01-17

- name: Deploy web application
  hosts: webservers
  become: true
  gather_facts: true
  
  vars:
    app_name: myapp
    app_version: "1.0.0"
    app_port: 8080
  
  pre_tasks:
    - name: Update package cache
      ansible.builtin.apt:
        update_cache: true
        cache_valid_time: 3600
      when: ansible_os_family == "Debian"
  
  roles:
    - role: common
    - role: webserver
    - role: application
  
  tasks:
    - name: Ensure application is running
      ansible.builtin.systemd:
        name: "{{ app_name }}"
        state: started
        enabled: true
  
  post_tasks:
    - name: Verify application health
      ansible.builtin.uri:
        url: "http://localhost:{{ app_port }}/health"
        status_code: 200
      register: health_check
      retries: 5
      delay: 10
  
  handlers:
    - name: Restart application
      ansible.builtin.systemd:
        name: "{{ app_name }}"
        state: restarted
```

## Task Writing

### Idempotent Tasks
```yaml
---
# Always use fully qualified collection names (FQCN)
- name: Create application directory
  ansible.builtin.file:
    path: /opt/myapp
    state: directory
    owner: appuser
    group: appuser
    mode: '0755'

- name: Copy application configuration
  ansible.builtin.template:
    src: app.conf.j2
    dest: /etc/myapp/app.conf
    owner: appuser
    group: appuser
    mode: '0644'
    validate: '/usr/bin/myapp --validate-config %s'
  notify: Restart application

- name: Install packages
  ansible.builtin.package:
    name:
      - nginx
      - python3
      - git
    state: present

- name: Ensure service is running
  ansible.builtin.systemd:
    name: nginx
    state: started
    enabled: true
```

### Task Names
```yaml
---
# Good: Descriptive and specific
- name: Install PostgreSQL 14 on Ubuntu
  ansible.builtin.apt:
    name: postgresql-14
    state: present

# Good: Action and target clear
- name: Copy application configuration to /etc/myapp
  ansible.builtin.copy:
    src: app.conf
    dest: /etc/myapp/app.conf

# Bad: Too generic
- name: Install package
  ansible.builtin.package:
    name: nginx

# Bad: Not descriptive
- name: Copy file
  ansible.builtin.copy:
    src: file
    dest: /tmp/file
```

## Variables

### Variable Precedence (lowest to highest)
1. Role defaults (`role/defaults/main.yml`)
2. Inventory file vars
3. Inventory `group_vars/all`
4. Inventory `group_vars/*`
5. Inventory `host_vars/*`
6. Playbook group_vars
7. Playbook host_vars
8. Host facts
9. Play vars
10. Task vars
11. Extra vars (`-e` on command line)

### Variable Organization
```yaml
# group_vars/all.yml - Common variables
---
timezone: "UTC"
ntp_servers:
  - 0.pool.ntp.org
  - 1.pool.ntp.org

# group_vars/webservers.yml - Web server specific
---
nginx_worker_processes: auto
nginx_worker_connections: 1024
ssl_certificate_path: /etc/ssl/certs

# host_vars/web01.yml - Host specific
---
server_id: 1
backup_enabled: true

# Variable naming
app_name: myapp                 # Good: descriptive
app_version: "1.0.0"           # Good: specific
x: test                        # Bad: not descriptive
```

### Using Variables
```yaml
---
- name: Configure application
  ansible.builtin.template:
    src: app.conf.j2
    dest: "/etc/{{ app_name }}/app.conf"
    
- name: Display message
  ansible.builtin.debug:
    msg: "Deploying {{ app_name }} version {{ app_version }}"

# Accessing nested variables
- name: Show database host
  ansible.builtin.debug:
    msg: "Database host: {{ database.host }}"
  vars:
    database:
      host: localhost
      port: 5432

# Default values
- name: Use default port if not specified
  ansible.builtin.debug:
    msg: "Port: {{ app_port | default(8080) }}"
```

## Handlers

### Handler Best Practices
```yaml
---
# handlers/main.yml
- name: Restart nginx
  ansible.builtin.systemd:
    name: nginx
    state: restarted

- name: Reload nginx
  ansible.builtin.systemd:
    name: nginx
    state: reloaded

- name: Restart application
  ansible.builtin.systemd:
    name: "{{ app_name }}"
    state: restarted

# Using handlers in tasks
- name: Update nginx configuration
  ansible.builtin.template:
    src: nginx.conf.j2
    dest: /etc/nginx/nginx.conf
  notify:
    - Reload nginx

- name: Update application binary
  ansible.builtin.copy:
    src: myapp
    dest: /usr/local/bin/myapp
    mode: '0755'
  notify:
    - Restart application
```

## Roles

### Role Directory Structure
```
roles/
└── webserver/
    ├── README.md
    ├── defaults/
    │   └── main.yml
    ├── files/
    │   └── index.html
    ├── handlers/
    │   └── main.yml
    ├── meta/
    │   └── main.yml
    ├── tasks/
    │   ├── main.yml
    │   ├── install.yml
    │   └── configure.yml
    ├── templates/
    │   └── nginx.conf.j2
    └── vars/
        └── main.yml
```

### Role Definition
```yaml
# roles/webserver/meta/main.yml
---
galaxy_info:
  author: DevOps Team
  description: Web server role
  company: Company Name
  license: MIT
  min_ansible_version: "2.14"
  
  platforms:
    - name: Ubuntu
      versions:
        - focal
        - jammy
    - name: Debian
      versions:
        - bullseye
  
  galaxy_tags:
    - web
    - nginx

dependencies:
  - role: common
    vars:
      timezone: "UTC"

# roles/webserver/defaults/main.yml
---
nginx_version: latest
nginx_port: 80
nginx_ssl_port: 443
nginx_worker_processes: auto

# roles/webserver/tasks/main.yml
---
- name: Include OS-specific variables
  ansible.builtin.include_vars: "{{ ansible_os_family }}.yml"

- name: Install web server
  ansible.builtin.include_tasks: install.yml

- name: Configure web server
  ansible.builtin.include_tasks: configure.yml
  tags:
    - config

# roles/webserver/tasks/install.yml
---
- name: Install nginx on Debian/Ubuntu
  ansible.builtin.apt:
    name: nginx
    state: present
    update_cache: true
  when: ansible_os_family == "Debian"

- name: Install nginx on RedHat/CentOS
  ansible.builtin.yum:
    name: nginx
    state: present
  when: ansible_os_family == "RedHat"
```

## Templates

### Jinja2 Templates
```jinja2
{# templates/nginx.conf.j2 #}
# Generated by Ansible - Do not edit manually
user {{ nginx_user }};
worker_processes {{ nginx_worker_processes }};

events {
    worker_connections {{ nginx_worker_connections }};
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    
    {% if enable_logging %}
    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;
    {% endif %}
    
    {% for server in nginx_servers %}
    server {
        listen {{ server.port }};
        server_name {{ server.name }};
        
        location / {
            proxy_pass http://{{ server.backend }};
        }
    }
    {% endfor %}
}
```

### Template Usage
```yaml
---
- name: Deploy nginx configuration
  ansible.builtin.template:
    src: nginx.conf.j2
    dest: /etc/nginx/nginx.conf
    owner: root
    group: root
    mode: '0644'
    backup: true
    validate: 'nginx -t -c %s'
  notify: Reload nginx
```

## Conditionals

### When Statements
```yaml
---
- name: Install on Debian systems
  ansible.builtin.apt:
    name: package
    state: present
  when: ansible_os_family == "Debian"

- name: Multiple conditions (AND)
  ansible.builtin.debug:
    msg: "Condition met"
  when:
    - ansible_distribution == "Ubuntu"
    - ansible_distribution_version == "22.04"

- name: Multiple conditions (OR)
  ansible.builtin.debug:
    msg: "Condition met"
  when: >
    ansible_distribution == "Ubuntu" or
    ansible_distribution == "Debian"

- name: Check variable is defined
  ansible.builtin.debug:
    msg: "Variable is defined"
  when: my_var is defined

- name: Check if service exists
  ansible.builtin.systemd:
    name: myservice
    state: started
  when: ansible_facts.services['myservice.service'] is defined
```

## Loops

### Loop Examples
```yaml
---
# Simple loop
- name: Create multiple directories
  ansible.builtin.file:
    path: "/opt/{{ item }}"
    state: directory
  loop:
    - app1
    - app2
    - app3

# Loop over dictionary
- name: Create users
  ansible.builtin.user:
    name: "{{ item.name }}"
    groups: "{{ item.groups }}"
    state: present
  loop:
    - name: alice
      groups: developers
    - name: bob
      groups: operators

# Loop with index
- name: Create numbered files
  ansible.builtin.file:
    path: "/tmp/file{{ item.0 }}.txt"
    state: touch
  loop: "{{ range(1, 6) | list }}"

# Loop with condition
- name: Install packages only on Ubuntu
  ansible.builtin.apt:
    name: "{{ item }}"
    state: present
  loop: "{{ packages }}"
  when: ansible_distribution == "Ubuntu"

# Nested loops
- name: Create directory structure
  ansible.builtin.file:
    path: "/opt/{{ item.0 }}/{{ item.1 }}"
    state: directory
  loop: "{{ apps | product(environments) | list }}"
  vars:
    apps: [app1, app2]
    environments: [dev, staging, prod]
```

## Error Handling

### Block and Rescue
```yaml
---
- name: Handle errors gracefully
  block:
    - name: Attempt to download file
      ansible.builtin.get_url:
        url: https://example.com/file.tar.gz
        dest: /tmp/file.tar.gz
    
    - name: Extract archive
      ansible.builtin.unarchive:
        src: /tmp/file.tar.gz
        dest: /opt/app
        remote_src: true
  
  rescue:
    - name: Log error
      ansible.builtin.debug:
        msg: "Failed to download or extract file"
    
    - name: Use fallback file
      ansible.builtin.copy:
        src: fallback.tar.gz
        dest: /tmp/file.tar.gz
  
  always:
    - name: Cleanup temporary files
      ansible.builtin.file:
        path: /tmp/file.tar.gz
        state: absent

# Ignore errors
- name: Command that might fail
  ansible.builtin.command: /usr/bin/might-fail
  ignore_errors: true
  register: result

- name: React to failure
  ansible.builtin.debug:
    msg: "Command failed but continuing"
  when: result is failed

# Failed when
- name: Check service status
  ansible.builtin.command: systemctl status myservice
  register: service_status
  failed_when: "'active' not in service_status.stdout"
```

## Tags

### Using Tags
```yaml
---
- name: Install packages
  ansible.builtin.apt:
    name: nginx
    state: present
  tags:
    - install
    - packages

- name: Configure application
  ansible.builtin.template:
    src: app.conf.j2
    dest: /etc/app/app.conf
  tags:
    - config
    - never  # Only run when explicitly specified

- name: Deploy application
  ansible.builtin.copy:
    src: app.bin
    dest: /usr/local/bin/app
  tags:
    - deploy
    - always  # Always run unless --skip-tags is used
```

```bash
# Run specific tags
ansible-playbook playbook.yml --tags "install,config"

# Skip specific tags
ansible-playbook playbook.yml --skip-tags "deploy"

# List all tags
ansible-playbook playbook.yml --list-tags
```

## Vault

### Using Ansible Vault
```bash
# Create encrypted file
ansible-vault create secrets.yml

# Edit encrypted file
ansible-vault edit secrets.yml

# Encrypt existing file
ansible-vault encrypt vars/passwords.yml

# Decrypt file
ansible-vault decrypt vars/passwords.yml

# View encrypted file
ansible-vault view secrets.yml

# Rekey (change password)
ansible-vault rekey secrets.yml
```

### Vault in Playbooks
```yaml
---
# Encrypted variables file
# vars/secrets.yml (encrypted)
database_password: supersecret
api_key: secretkey123

# Using encrypted variables
- name: Deploy with secrets
  hosts: all
  vars_files:
    - vars/secrets.yml
  
  tasks:
    - name: Configure database
      ansible.builtin.template:
        src: database.conf.j2
        dest: /etc/app/database.conf
```

```bash
# Run playbook with vault password
ansible-playbook playbook.yml --ask-vault-pass

# Use password file
ansible-playbook playbook.yml --vault-password-file .vault_pass
```

## Dynamic Inventory

### Cloud Inventory Plugin
```yaml
# inventory/azure_rm.yml
plugin: azure.azcollection.azure_rm

# Authentication
auth_source: auto

# Filters
include_vm_resource_groups:
  - myapp-prod
  - myapp-staging

# Grouping
keyed_groups:
  - key: tags.environment
    prefix: env
  - key: tags.application
    prefix: app

# Conditional groups
conditional_groups:
  webservers: "'web' in tags.role"
  databases: "'db' in tags.role"
```

```bash
# Test inventory
ansible-inventory -i inventory/azure_rm.yml --list
ansible-inventory -i inventory/azure_rm.yml --graph
```

## Testing

### Ansible Lint
```yaml
# .ansible-lint
---
profile: production

exclude_paths:
  - .github/
  - test/

skip_list:
  - experimental  # Allow experimental features

warn_list:
  - no-changed-when
  - no-handler

# Custom rules
rules:
  line-length:
    max: 120
```

```bash
# Run ansible-lint
ansible-lint playbook.yml

# Auto-fix issues
ansible-lint --fix playbook.yml
```

### Molecule Testing
```yaml
# molecule/default/molecule.yml
---
dependency:
  name: galaxy

driver:
  name: docker

platforms:
  - name: ubuntu22
    image: ubuntu:22.04
    pre_build_image: true

provisioner:
  name: ansible
  config_options:
    defaults:
      callbacks_enabled: profile_tasks

verifier:
  name: ansible

scenario:
  test_sequence:
    - dependency
    - cleanup
    - destroy
    - syntax
    - create
    - prepare
    - converge
    - idempotence
    - verify
    - destroy
```

```bash
# Run molecule tests
molecule test

# Test specific scenario
molecule test -s ubuntu
```

## Best Practices Checklist

- ✅ Use fully qualified collection names (FQCN)
- ✅ All tasks have descriptive names
- ✅ Use handlers for service restarts
- ✅ Implement idempotency in all tasks
- ✅ Use ansible-vault for sensitive data
- ✅ Organize with roles for reusability
- ✅ Use tags for selective execution
- ✅ Variables in appropriate locations
- ✅ Comments for complex logic
- ✅ Test with ansible-lint
- ✅ Validate templates and configs
- ✅ Use blocks for error handling
- ✅ Document roles with README
- ✅ Version control all playbooks and roles

