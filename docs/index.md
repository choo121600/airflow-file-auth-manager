# airflow-file-auth-manager Documentation

Welcome to the official documentation for **airflow-file-auth-manager**, a lightweight YAML file-based Auth Manager for Apache Airflow 3.x.

## What is airflow-file-auth-manager?

airflow-file-auth-manager is an authentication plugin for Apache Airflow that stores user credentials in a simple YAML file. It provides:

- **Simple Setup**: No external services required
- **Secure Storage**: bcrypt password hashing
- **Role-Based Access**: Three-tier permission system
- **CLI Management**: Easy user administration from command line

## Who Should Use This?

This auth manager is ideal for:

- Small teams (1-3 people)
- Development and staging environments
- Self-hosted Airflow deployments
- Situations where LDAP/OAuth is overkill

For larger teams or enterprise deployments, consider using [airflow-ldap-auth-manager](https://github.com/emredjan/airflow-ldap-auth-manager) or the FAB auth manager with a proper database backend.

## Documentation

| Document | Description |
|----------|-------------|
| [Installation](installation.md) | How to install and set up the auth manager |
| [Configuration](configuration.md) | Configuration options and settings |
| [User Management](user-management.md) | Managing users via CLI and YAML |
| [Roles & Permissions](roles.md) | Understanding the role-based access control |
| [API Authentication](api.md) | Using JWT tokens for API access |
| [Security](security.md) | Security best practices and considerations |

## Quick Example

```bash
# 1. Install the package
pip install airflow-file-auth-manager

# 2. Create users file with admin user
python -m airflow_file_auth_manager.cli init -f users.yaml

# 3. Configure Airflow
export AIRFLOW__CORE__AUTH_MANAGER=airflow_file_auth_manager.FileAuthManager
export AIRFLOW_FILE_AUTH_USERS_FILE=$(pwd)/users.yaml

# 4. Start Airflow
airflow standalone
```

## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                   Apache Airflow 3.x                     │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │              FileAuthManager                       │  │
│  │  ┌──────────────┐  ┌──────────────┐               │  │
│  │  │  UserStore   │  │ FileAuthPolicy│               │  │
│  │  │  (YAML I/O)  │  │ (RBAC Rules) │               │  │
│  │  └──────┬───────┘  └──────────────┘               │  │
│  │         │                                          │  │
│  │  ┌──────▼───────┐  ┌──────────────┐               │  │
│  │  │ users.yaml   │  │  FastAPI App │               │  │
│  │  │ (encrypted)  │  │ /auth/file/* │               │  │
│  │  └──────────────┘  └──────────────┘               │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

## Requirements

- Python 3.11+
- Apache Airflow 3.0+
- bcrypt 4.0+
- PyYAML 6.0+
- FastAPI 0.110+

## License

Apache License 2.0

## Support

- [GitHub Issues](https://github.com/yeonguk/airflow-file-auth-manager/issues)
- [GitHub Discussions](https://github.com/yeonguk/airflow-file-auth-manager/discussions)
