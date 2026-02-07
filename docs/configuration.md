# Configuration Guide

This guide covers all configuration options for airflow-file-auth-manager.

## Configuration Methods

Configuration can be set via:

1. **airflow.cfg** - Traditional Airflow configuration file
2. **Environment Variables** - Using Airflow's standard format
3. **Astro settings** - For Astronomer deployments

## Core Configuration

### Auth Manager Selection

The auth manager must be specified in Airflow's core configuration:

```ini
[core]
auth_manager = airflow_file_auth_manager.FileAuthManager
```

Or via environment variable:

```bash
export AIRFLOW__CORE__AUTH_MANAGER=airflow_file_auth_manager.FileAuthManager
```

## File Auth Manager Settings

All settings go under the `[file_auth_manager]` section.

### users_file

**Type:** String (path)
**Default:** `$AIRFLOW_HOME/users.yaml`
**Description:** Path to the YAML file containing user definitions.

```ini
[file_auth_manager]
users_file = /etc/airflow/users.yaml
```

Environment variable:

```bash
export AIRFLOW__FILE_AUTH_MANAGER__USERS_FILE=/etc/airflow/users.yaml
# or
export AIRFLOW_FILE_AUTH_USERS_FILE=/etc/airflow/users.yaml
```

## JWT Token Settings

JWT settings are configured under `[api_auth]` section (shared with Airflow).

### jwt_expiration_seconds

**Type:** Integer
**Default:** `36000` (10 hours)
**Description:** How long JWT tokens remain valid.

```ini
[api_auth]
jwt_expiration_seconds = 3600  # 1 hour
```

## Complete Configuration Example

### airflow.cfg

```ini
[core]
auth_manager = airflow_file_auth_manager.FileAuthManager

[file_auth_manager]
users_file = /opt/airflow/config/users.yaml

[api_auth]
jwt_expiration_seconds = 28800
```

### Environment Variables

```bash
# Core auth manager
export AIRFLOW__CORE__AUTH_MANAGER=airflow_file_auth_manager.FileAuthManager

# Users file location
export AIRFLOW_FILE_AUTH_USERS_FILE=/opt/airflow/config/users.yaml

# JWT expiration (8 hours)
export AIRFLOW__API_AUTH__JWT_EXPIRATION_SECONDS=28800
```

### Docker Compose

```yaml
version: '3.8'
services:
  airflow:
    image: apache/airflow:3.0.0
    environment:
      - AIRFLOW__CORE__AUTH_MANAGER=airflow_file_auth_manager.FileAuthManager
      - AIRFLOW_FILE_AUTH_USERS_FILE=/opt/airflow/users.yaml
      - AIRFLOW__API_AUTH__JWT_EXPIRATION_SECONDS=28800
    volumes:
      - ./users.yaml:/opt/airflow/users.yaml:ro
```

### Kubernetes ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: airflow-config
data:
  AIRFLOW__CORE__AUTH_MANAGER: "airflow_file_auth_manager.FileAuthManager"
  AIRFLOW_FILE_AUTH_USERS_FILE: "/opt/airflow/config/users.yaml"
  AIRFLOW__API_AUTH__JWT_EXPIRATION_SECONDS: "28800"
```

### Astro Project (airflow_settings.yaml)

```yaml
airflow:
  config:
    AIRFLOW__CORE__AUTH_MANAGER: "airflow_file_auth_manager.FileAuthManager"
    AIRFLOW__API_AUTH__JWT_EXPIRATION_SECONDS: "28800"
  env_vars:
    AIRFLOW_FILE_AUTH_USERS_FILE: "/usr/local/airflow/users.yaml"
```

## Users File Location Strategy

### Development

Store in project directory:

```
my-airflow-project/
├── dags/
├── users.yaml          # Development users
└── airflow.cfg
```

### Production (Docker/Kubernetes)

Mount as read-only volume:

```yaml
volumes:
  - ./config/users.yaml:/opt/airflow/users.yaml:ro
```

### Production (Bare Metal)

Store in system config directory:

```
/etc/airflow/
├── airflow.cfg
└── users.yaml          # chmod 600, owned by airflow user
```

## Configuration Validation

### Verify Configuration

```bash
# Check if auth manager is configured
airflow config get-value core auth_manager

# Check users file path
python -c "
from airflow.configuration import conf
print(conf.get('file_auth_manager', 'users_file', fallback='Not set'))
"
```

### Test User Authentication

```bash
# Try to get a token
curl -X POST http://localhost:8080/auth/file/token \
    -H "Content-Type: application/json" \
    -d '{"username": "admin", "password": "your_password"}'
```

## Advanced Configuration

### Multiple Environments

Use environment-specific users files:

```bash
# Development
export AIRFLOW_FILE_AUTH_USERS_FILE=./users.dev.yaml

# Staging
export AIRFLOW_FILE_AUTH_USERS_FILE=./users.staging.yaml

# Production
export AIRFLOW_FILE_AUTH_USERS_FILE=/etc/airflow/users.yaml
```

### Hot Reloading Users

The users file is loaded at startup. To reload without restart:

```python
# From within a Dag or Python shell
from airflow_file_auth_manager import UserStore
store = UserStore("/path/to/users.yaml")
store.reload()
```

Note: This only affects the current process. For multi-process deployments, restart the webserver.

## Troubleshooting

### "Users file not found"

Check the file path and permissions:

```bash
# Verify path
ls -la /path/to/users.yaml

# Check from Airflow's perspective
python -c "
import os
path = os.environ.get('AIRFLOW_FILE_AUTH_USERS_FILE', 'users.yaml')
print(f'Path: {path}')
print(f'Exists: {os.path.exists(path)}')
print(f'Readable: {os.access(path, os.R_OK)}')
"
```

### Configuration Not Taking Effect

1. Ensure no conflicting settings in multiple config sources
2. Restart all Airflow components (webserver, scheduler, workers)
3. Check for typos in configuration keys

```bash
# View all current configuration
airflow config list | grep -i auth
```
