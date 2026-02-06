# airflow-file-auth-manager

A lightweight YAML file-based Auth Manager for Apache Airflow 3.x

[![PyPI version](https://badge.fury.io/py/airflow-file-auth-manager.svg)](https://pypi.org/project/airflow-file-auth-manager/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Apache Airflow 3.x](https://img.shields.io/badge/airflow-3.x-017cee.svg)](https://airflow.apache.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![CI](https://github.com/choo121600/airflow-file-auth-manager/actions/workflows/ci.yml/badge.svg)](https://github.com/choo121600/airflow-file-auth-manager/actions/workflows/ci.yml)

## Overview

**airflow-file-auth-manager** provides simple file-based authentication for Apache Airflow 3.x without requiring LDAP or external authentication services. Perfect for small teams of 1-3 people who need basic authentication with role-based access control.

### Key Features

- **Secure Password Storage**: bcrypt hashing with configurable work factor
- **Three-Tier Role System**: Admin, Editor, and Viewer roles
- **JWT Token Authentication**: Stateless session management
- **YAML-Based Configuration**: Simple, human-readable user management
- **CLI Tools**: Command-line interface for user administration
- **Modern Login UI**: Clean, responsive login page

## Installation

### From PyPI

```bash
pip install airflow-file-auth-manager
```

### From Source

```bash
git clone https://github.com/choo121600/airflow-file-auth-manager.git
cd airflow-file-auth-manager
pip install -e .
```

## Quick Start

### 1. Create Users File

```bash
# Initialize with an admin user
python -m airflow_file_auth_manager.cli init \
    -f /path/to/users.yaml \
    -e admin@example.com

# Add additional users
python -m airflow_file_auth_manager.cli add-user \
    -f /path/to/users.yaml \
    -u developer \
    -r editor \
    -e dev@example.com
```

### 2. Configure Airflow

Add to your `airflow.cfg`:

```ini
[core]
auth_manager = airflow_file_auth_manager.FileAuthManager

[file_auth_manager]
users_file = /path/to/users.yaml
```

Or use environment variables:

```bash
export AIRFLOW__CORE__AUTH_MANAGER=airflow_file_auth_manager.FileAuthManager
export AIRFLOW_FILE_AUTH_USERS_FILE=/path/to/users.yaml
```

### 3. Start Airflow

```bash
airflow standalone
# or
astro dev start
```

## Role-Based Access Control

| Role | Description |
|------|-------------|
| **Admin** | Full access including Connection, Variable, Pool, and Configuration management |
| **Editor** | DAG execution and management, read access to all resources |
| **Viewer** | Read-only access to all resources |

### Permission Matrix

| Resource | Viewer | Editor | Admin |
|----------|--------|--------|-------|
| DAGs (view) | ✅ | ✅ | ✅ |
| DAGs (trigger/manage) | ❌ | ✅ | ✅ |
| Connections (view) | ✅ | ✅ | ✅ |
| Connections (modify) | ❌ | ❌ | ✅ |
| Variables (view) | ✅ | ✅ | ✅ |
| Variables (modify) | ❌ | ❌ | ✅ |
| Pools (view) | ✅ | ✅ | ✅ |
| Pools (modify) | ❌ | ❌ | ✅ |
| Configuration | ✅ (read) | ✅ (read) | ✅ |

## Users File Format

```yaml
version: "1.0"
users:
  - username: admin
    password_hash: "$2b$12$..."  # bcrypt hash
    role: admin
    email: admin@example.com
    first_name: Admin
    last_name: User
    active: true

  - username: developer
    password_hash: "$2b$12$..."
    role: editor
    email: dev@example.com
    active: true

  - username: analyst
    password_hash: "$2b$12$..."
    role: viewer
    email: analyst@example.com
    active: true
```

## CLI Reference

### Initialize Users File

```bash
python -m airflow_file_auth_manager.cli init \
    -f users.yaml \
    [-p password] \
    [-e email] \
    [--force]
```

### Add User

```bash
python -m airflow_file_auth_manager.cli add-user \
    -f users.yaml \
    -u username \
    -r admin|editor|viewer \
    [-p password] \
    [-e email] \
    [--firstname "First"] \
    [--lastname "Last"]
```

### Update User

```bash
python -m airflow_file_auth_manager.cli update-user \
    -f users.yaml \
    -u username \
    [-p]  # Prompt for new password
    [-r role] \
    [-e email] \
    [--active true|false]
```

### Delete User

```bash
python -m airflow_file_auth_manager.cli delete-user \
    -f users.yaml \
    -u username \
    [-y]  # Skip confirmation
```

### List Users

```bash
python -m airflow_file_auth_manager.cli list-users -f users.yaml
```

### Generate Password Hash

```bash
python -m airflow_file_auth_manager.cli hash-password [-p password]
```

## API Authentication

### Obtain Token

```bash
curl -X POST http://localhost:8080/auth/file/token \
    -H "Content-Type: application/json" \
    -d '{"username": "admin", "password": "your_password"}'
```

Response:

```json
{
    "access_token": "eyJ...",
    "token_type": "Bearer",
    "expires_in": 36000
}
```

### Use Token

```bash
curl http://localhost:8080/api/v1/dags \
    -H "Authorization: Bearer eyJ..."
```

## Configuration Options

### airflow.cfg

```ini
[file_auth_manager]
# Path to users YAML file
users_file = /opt/airflow/users.yaml

[api_auth]
# JWT token expiration in seconds (default: 36000 = 10 hours)
jwt_expiration_seconds = 36000
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `AIRFLOW_FILE_AUTH_USERS_FILE` | Path to users YAML file |
| `AIRFLOW__FILE_AUTH_MANAGER__USERS_FILE` | Alternative config path |

## Security Considerations

1. **Protect the users file**: Set appropriate permissions (`chmod 600 users.yaml`)
2. **Use strong passwords**: Enforce password policies in your organization
3. **Secure file location**: Store outside web-accessible directories
4. **Regular rotation**: Periodically update passwords
5. **HTTPS**: Always use HTTPS in production for secure cookie transmission

## Development

### Setup

```bash
git clone https://github.com/yeonguk/airflow-file-auth-manager.git
cd airflow-file-auth-manager
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest tests/ -v
```

### Run Tests with Coverage

```bash
pytest tests/ -v --cov=airflow_file_auth_manager --cov-report=html
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Apache Airflow 3.x                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐    ┌─────────────────┐                │
│  │  FileAuthManager │◄───│  BaseAuthManager │                │
│  └────────┬────────┘    └─────────────────┘                │
│           │                                                 │
│  ┌────────▼────────┐    ┌─────────────────┐                │
│  │   UserStore     │◄───│   users.yaml    │                │
│  └────────┬────────┘    └─────────────────┘                │
│           │                                                 │
│  ┌────────▼────────┐    ┌─────────────────┐                │
│  │ FileAuthPolicy  │    │   FastAPI App   │                │
│  │ (RBAC rules)    │    │ (login/logout)  │                │
│  └─────────────────┘    └─────────────────┘                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Comparison with Other Auth Managers

| Feature | File Auth | Simple Auth | FAB Auth | LDAP Auth |
|---------|-----------|-------------|----------|-----------|
| External Dependencies | None | None | Database | LDAP Server |
| Password Storage | bcrypt | Plain text | Database | LDAP |
| Role System | 3 roles | 4 roles | Flexible | Group-based |
| User Management | YAML + CLI | Config | Web UI | LDAP Admin |
| Production Ready | Yes | No | Yes | Yes |
| Best For | Small teams | Development | Medium teams | Enterprise |

## Troubleshooting

### Common Issues

**"Users file not found"**
- Ensure the file path is correct and accessible
- Check file permissions

**"Invalid username or password"**
- Verify the password hash was generated correctly
- Check if the user is marked as `active: true`

**"Module not found: airflow"**
- The CLI works without Airflow for basic operations
- Install Airflow for full functionality

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Apache Airflow](https://airflow.apache.org/) - The workflow orchestration platform
- [airflow-ldap-auth-manager](https://github.com/emredjan/airflow-ldap-auth-manager) - Inspiration for the architecture
