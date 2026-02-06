# Installation Guide

This guide covers the installation and initial setup of airflow-file-auth-manager.

## Prerequisites

Before installing, ensure you have:

- Python 3.11 or higher
- Apache Airflow 3.0 or higher
- pip package manager

## Installation Methods

### Method 1: Install from PyPI (Recommended)

```bash
pip install airflow-file-auth-manager
```

### Method 2: Install from Source

```bash
# Clone the repository
git clone https://github.com/yeonguk/airflow-file-auth-manager.git
cd airflow-file-auth-manager

# Install in development mode
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

### Method 3: Install in Astro Project

Add to your `requirements.txt`:

```
airflow-file-auth-manager>=0.1.0
```

Or install directly in your Dockerfile:

```dockerfile
FROM quay.io/astronomer/astro-runtime:12.0.0

# Install file auth manager
RUN pip install airflow-file-auth-manager
```

## Initial Setup

### Step 1: Create Users File

Initialize a users file with an admin user:

```bash
python -m airflow_file_auth_manager.cli init \
    -f /path/to/users.yaml \
    -e admin@yourcompany.com
```

You'll be prompted to enter a password for the admin user.

### Step 2: Configure Airflow

#### Option A: Using airflow.cfg

Add these lines to your `airflow.cfg`:

```ini
[core]
auth_manager = airflow_file_auth_manager.FileAuthManager

[file_auth_manager]
users_file = /path/to/users.yaml
```

#### Option B: Using Environment Variables

```bash
export AIRFLOW__CORE__AUTH_MANAGER=airflow_file_auth_manager.FileAuthManager
export AIRFLOW_FILE_AUTH_USERS_FILE=/path/to/users.yaml
```

#### Option C: Using Astro CLI (airflow_settings.yaml)

```yaml
airflow:
  config:
    AIRFLOW__CORE__AUTH_MANAGER: "airflow_file_auth_manager.FileAuthManager"
  env_vars:
    AIRFLOW_FILE_AUTH_USERS_FILE: "/usr/local/airflow/users.yaml"
```

### Step 3: Verify Installation

Start Airflow and verify the login page appears:

```bash
# Using standalone mode
airflow standalone

# Using Astro CLI
astro dev start
```

Navigate to `http://localhost:8080` and you should see the File Auth Manager login page.

## Upgrading

### From Previous Versions

```bash
pip install --upgrade airflow-file-auth-manager
```

The users.yaml format is backward compatible. No migration is required.

### Version Compatibility

| airflow-file-auth-manager | Apache Airflow |
|---------------------------|----------------|
| 0.1.x                     | 3.0.x - 3.1.x  |

## Uninstallation

### Remove the Package

```bash
pip uninstall airflow-file-auth-manager
```

### Revert Airflow Configuration

Update your `airflow.cfg` to use a different auth manager:

```ini
[core]
# Use Simple Auth Manager for development
auth_manager = airflow.auth.managers.simple.simple_auth_manager.SimpleAuthManager

# Or use FAB Auth Manager
# auth_manager = airflow.providers.fab.auth_manager.fab_auth_manager.FabAuthManager
```

## Troubleshooting Installation

### ModuleNotFoundError: No module named 'airflow_file_auth_manager'

Ensure the package is installed in the same Python environment as Airflow:

```bash
# Check which Python Airflow is using
which airflow
# Install in that environment
pip install airflow-file-auth-manager
```

### Permission Denied for users.yaml

Ensure the Airflow process has read access to the users file:

```bash
chmod 644 users.yaml
# Or for stricter security (owner read/write only)
chmod 600 users.yaml
chown airflow:airflow users.yaml
```

### Airflow Won't Start After Configuration

Check for syntax errors in your configuration:

```bash
# Verify the module can be imported
python -c "from airflow_file_auth_manager import FileAuthManager; print('OK')"
```

## Next Steps

After installation:

1. [Configure additional options](configuration.md)
2. [Add more users](user-management.md)
3. [Understand roles and permissions](roles.md)
