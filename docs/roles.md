# Roles & Permissions Guide

This guide explains the role-based access control (RBAC) system in airflow-file-auth-manager.

## Role Hierarchy

airflow-file-auth-manager uses a simple three-tier role hierarchy:

```
Admin (Level 3)
   ↓
Editor (Level 2)
   ↓
Viewer (Level 1)
```

Higher roles inherit all permissions from lower roles.

## Role Definitions

### Viewer

**Level:** 1 (Lowest)
**Purpose:** Read-only monitoring access

Viewers can:
- View all Dags and their status
- View Dag runs and task instances
- View logs
- View connections (not secrets)
- View variables (not sensitive values)
- View pools
- View configuration
- Access all read-only API endpoints

Viewers cannot:
- Trigger or manage Dag runs
- Create, modify, or delete any resources

**Best for:** Stakeholders, on-call engineers, auditors

### Editor

**Level:** 2 (Middle)
**Purpose:** Dag management and execution

Editors can do everything Viewers can, plus:
- Trigger Dag runs
- Pause/unpause Dags
- Clear task instances
- Mark tasks as success/failed
- Manage backfills
- Manage datasets/assets

Editors cannot:
- Create, modify, or delete connections
- Create, modify, or delete variables
- Manage pools
- Modify configuration

**Best for:** Data engineers, developers, operators

### Admin

**Level:** 3 (Highest)
**Purpose:** Full system administration

Admins can do everything, including:
- All Viewer and Editor permissions
- Create, modify, delete connections
- Create, modify, delete variables
- Manage pools
- View and modify configuration
- Access all admin endpoints

**Best for:** Platform admins, DevOps engineers, lead developers

## Permission Matrix

### Dag Permissions

| Action | Viewer | Editor | Admin |
|--------|--------|--------|-------|
| View Dag list | ✅ | ✅ | ✅ |
| View Dag details | ✅ | ✅ | ✅ |
| View Dag code | ✅ | ✅ | ✅ |
| Trigger Dag run | ❌ | ✅ | ✅ |
| Pause/unpause Dag | ❌ | ✅ | ✅ |
| Delete Dag | ❌ | ✅ | ✅ |

### Dag Run Permissions

| Action | Viewer | Editor | Admin |
|--------|--------|--------|-------|
| View Dag runs | ✅ | ✅ | ✅ |
| View run details | ✅ | ✅ | ✅ |
| Clear Dag run | ❌ | ✅ | ✅ |
| Mark run success | ❌ | ✅ | ✅ |
| Mark run failed | ❌ | ✅ | ✅ |
| Delete Dag run | ❌ | ✅ | ✅ |

### Task Instance Permissions

| Action | Viewer | Editor | Admin |
|--------|--------|--------|-------|
| View task instances | ✅ | ✅ | ✅ |
| View task logs | ✅ | ✅ | ✅ |
| Clear task | ❌ | ✅ | ✅ |
| Mark task success | ❌ | ✅ | ✅ |
| Mark task failed | ❌ | ✅ | ✅ |

### Connection Permissions

| Action | Viewer | Editor | Admin |
|--------|--------|--------|-------|
| List connections | ✅ | ✅ | ✅ |
| View connection | ✅ | ✅ | ✅ |
| Create connection | ❌ | ❌ | ✅ |
| Modify connection | ❌ | ❌ | ✅ |
| Delete connection | ❌ | ❌ | ✅ |
| Test connection | ❌ | ❌ | ✅ |

### Variable Permissions

| Action | Viewer | Editor | Admin |
|--------|--------|--------|-------|
| List variables | ✅ | ✅ | ✅ |
| View variable | ✅ | ✅ | ✅ |
| Create variable | ❌ | ❌ | ✅ |
| Modify variable | ❌ | ❌ | ✅ |
| Delete variable | ❌ | ❌ | ✅ |

### Pool Permissions

| Action | Viewer | Editor | Admin |
|--------|--------|--------|-------|
| List pools | ✅ | ✅ | ✅ |
| View pool | ✅ | ✅ | ✅ |
| Create pool | ❌ | ❌ | ✅ |
| Modify pool | ❌ | ❌ | ✅ |
| Delete pool | ❌ | ❌ | ✅ |

### Asset (Dataset) Permissions

| Action | Viewer | Editor | Admin |
|--------|--------|--------|-------|
| List assets | ✅ | ✅ | ✅ |
| View asset | ✅ | ✅ | ✅ |
| Trigger asset event | ❌ | ✅ | ✅ |

### Configuration Permissions

| Action | Viewer | Editor | Admin |
|--------|--------|--------|-------|
| View configuration | ✅ | ✅ | ✅ |
| Modify configuration | ❌ | ❌ | ✅ |

## HTTP Method Mapping

The authorization system maps HTTP methods to permission types:

| HTTP Method | Permission Type | Description |
|-------------|-----------------|-------------|
| GET | Read | View resources |
| POST | Write | Create resources, trigger actions |
| PUT | Write | Update resources |
| PATCH | Write | Partial update resources |
| DELETE | Write | Delete resources |

## Role Assignment Guidelines

### Principle of Least Privilege

Always assign the minimum role necessary:

```yaml
users:
  # Platform admin - needs full access
  - username: platform_admin
    role: admin

  # Data engineer - runs and manages Dags
  - username: data_engineer
    role: editor

  # Business analyst - only views dashboards
  - username: analyst
    role: viewer

  # Monitoring service - read-only API access
  - username: monitoring_bot
    role: viewer
```

### Role Escalation

Roles can be changed via CLI:

```bash
# Promote to admin
python -m airflow_file_auth_manager.cli update-user \
    -f users.yaml \
    -u data_engineer \
    -r admin

# Demote to viewer
python -m airflow_file_auth_manager.cli update-user \
    -f users.yaml \
    -u former_editor \
    -r viewer
```

## Custom Authorization Logic

### Extending the Policy

For custom authorization logic, extend `FileAuthPolicy`:

```python
from airflow_file_auth_manager.policy import FileAuthPolicy, Role

class CustomPolicy(FileAuthPolicy):
    @classmethod
    def is_authorized_dag(cls, *, method, user_role, access_entity=None, details=None):
        # Example: Restrict certain Dags to admins only
        if details and details.id.startswith("admin_"):
            return cls.has_minimum_role(user_role, Role.ADMIN)
        return super().is_authorized_dag(
            method=method,
            user_role=user_role,
            access_entity=access_entity,
            details=details,
        )
```

### Per-Dag Access Control

For per-Dag access control (e.g., team-based restrictions), consider:

1. Using Dag-level access controls in Airflow 3.x
2. Implementing custom middleware
3. Using a more flexible auth manager (FAB, LDAP)

## Troubleshooting

### "403 Forbidden" Errors

1. Check user's role:
   ```bash
   python -m airflow_file_auth_manager.cli list-users -f users.yaml | grep username
   ```

2. Verify the required permission for the action
3. Upgrade role if necessary

### Unexpected Access

1. Verify the user's role hasn't been changed
2. Check for multiple user entries with same username
3. Ensure the correct users.yaml is being used

## API Reference

### Check Authorization Programmatically

```python
from airflow_file_auth_manager.policy import FileAuthPolicy

# Check if editor can modify connections
can_modify = FileAuthPolicy.is_authorized_connection(
    method="POST",
    user_role="editor"
)
print(f"Editor can create connections: {can_modify}")  # False

# Check role hierarchy
has_role = FileAuthPolicy.has_minimum_role("editor", Role.VIEWER)
print(f"Editor has viewer permissions: {has_role}")  # True
```
