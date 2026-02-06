# User Management Guide

This guide covers how to create, modify, and manage users in airflow-file-auth-manager.

## CLI Tool

The primary way to manage users is through the command-line interface.

### Running the CLI

```bash
# If installed via pip
python -m airflow_file_auth_manager.cli <command>

# Or create an alias
alias file-auth="python -m airflow_file_auth_manager.cli"
file-auth <command>
```

## Creating Users

### Initialize First Admin

```bash
python -m airflow_file_auth_manager.cli init \
    -f users.yaml \
    -e admin@company.com
```

You'll be prompted for a password. This creates an `admin` user with full access.

### Add New User

```bash
python -m airflow_file_auth_manager.cli add-user \
    -f users.yaml \
    -u john.doe \
    -r editor \
    -e john.doe@company.com \
    --firstname "John" \
    --lastname "Doe"
```

### Add User with Password on Command Line

```bash
# Note: This may expose password in shell history
python -m airflow_file_auth_manager.cli add-user \
    -f users.yaml \
    -u service_account \
    -r viewer \
    -p "service_password_123"
```

## Updating Users

### Change Role

```bash
python -m airflow_file_auth_manager.cli update-user \
    -f users.yaml \
    -u john.doe \
    -r admin
```

### Change Password

```bash
# Interactive password prompt
python -m airflow_file_auth_manager.cli update-user \
    -f users.yaml \
    -u john.doe \
    -p
```

### Deactivate User

```bash
python -m airflow_file_auth_manager.cli update-user \
    -f users.yaml \
    -u john.doe \
    --active false
```

### Update Email

```bash
python -m airflow_file_auth_manager.cli update-user \
    -f users.yaml \
    -u john.doe \
    -e new.email@company.com
```

## Deleting Users

### With Confirmation

```bash
python -m airflow_file_auth_manager.cli delete-user \
    -f users.yaml \
    -u john.doe
# Prompts: Delete user 'john.doe'? [y/N]:
```

### Skip Confirmation

```bash
python -m airflow_file_auth_manager.cli delete-user \
    -f users.yaml \
    -u john.doe \
    -y
```

## Listing Users

### Basic List

```bash
python -m airflow_file_auth_manager.cli list-users -f users.yaml
```

Output:

```
Username             Role       Email                          Active
----------------------------------------------------------------------
admin                admin      admin@company.com              Yes
john.doe             editor     john.doe@company.com           Yes
jane.smith           viewer     jane.smith@company.com         Yes

Total: 3 user(s)
```

## Generating Password Hashes

### Interactive

```bash
python -m airflow_file_auth_manager.cli hash-password
# Prompts for password
```

### Non-Interactive

```bash
python -m airflow_file_auth_manager.cli hash-password -p "my_password"
# Outputs: $2b$12$...
```

Use this to manually edit the users.yaml file.

## Users File Format

### Complete Example

```yaml
version: "1.0"
users:
  - username: admin
    password_hash: "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4AwuLvQy1FLq/X5e"
    role: admin
    email: admin@company.com
    first_name: System
    last_name: Administrator
    active: true
    metadata:
      created_by: system
      created_at: "2024-01-15"

  - username: john.doe
    password_hash: "$2b$12$wYGJKFjGlXlqD.QzfqQjCeWtQHm3vLcL2vJJfKhOOWNqJ5zZV3X2W"
    role: editor
    email: john.doe@company.com
    first_name: John
    last_name: Doe
    active: true

  - username: jane.smith
    password_hash: "$2b$12$8hxKvN1vT5xXz.Ky7HqzheJ1WqOL2IJWL6Lf8NqJvGJe.F9VFqHyS"
    role: viewer
    email: jane.smith@company.com
    active: true

  - username: former.employee
    password_hash: "$2b$12$..."
    role: editor
    email: former@company.com
    active: false  # Deactivated, cannot login
```

### Field Reference

| Field | Required | Description |
|-------|----------|-------------|
| `username` | Yes | Unique identifier, used for login |
| `password_hash` | Yes | bcrypt hash of password |
| `role` | Yes | One of: `admin`, `editor`, `viewer` |
| `email` | No | User's email address |
| `first_name` | No | First name for display |
| `last_name` | No | Last name for display |
| `active` | No | Default: `true`. Set to `false` to disable login |
| `metadata` | No | Arbitrary key-value data |

## Manual File Editing

You can edit the YAML file directly. Remember to:

1. Use proper YAML syntax
2. Generate password hashes correctly
3. Maintain valid roles

### Generate Hash for Manual Entry

```bash
# Get the hash
python -m airflow_file_auth_manager.cli hash-password -p "new_password"
# Copy output to password_hash field
```

### Validate File After Editing

```bash
# Try to list users - will error if YAML is invalid
python -m airflow_file_auth_manager.cli list-users -f users.yaml
```

## Programmatic User Management

### Using Python API

```python
from airflow_file_auth_manager import UserStore

# Load user store
store = UserStore("/path/to/users.yaml")

# Add user
store.add_user(
    username="new.user",
    password="secure_password",
    role="editor",
    email="new.user@company.com"
)

# Save changes
store.save()

# Update user
store.update_user("new.user", role="admin")
store.save()

# Delete user
store.delete_user("new.user")
store.save()

# List all users
for user in store.get_all_users():
    print(f"{user.username}: {user.role}")
```

### Authenticate User

```python
from airflow_file_auth_manager import UserStore

store = UserStore("/path/to/users.yaml")
user = store.authenticate("username", "password")

if user:
    print(f"Authenticated: {user.username} ({user.role})")
else:
    print("Authentication failed")
```

## Best Practices

### Password Security

- Use strong, unique passwords (12+ characters)
- Never store plain text passwords
- Use `-p` flag only in scripts, not interactive sessions
- Rotate passwords periodically

### User Management

- Start users with minimum required role
- Deactivate users instead of deleting (audit trail)
- Use descriptive usernames
- Keep users file backed up

### File Security

```bash
# Restrict file permissions
chmod 600 users.yaml

# Ensure correct ownership
chown airflow:airflow users.yaml
```

## Troubleshooting

### "User already exists"

```bash
# Check if user exists
python -m airflow_file_auth_manager.cli list-users -f users.yaml | grep username
```

### "Invalid role"

Valid roles are: `admin`, `editor`, `viewer` (case-sensitive)

### Password Not Working

1. Regenerate the hash:
   ```bash
   python -m airflow_file_auth_manager.cli hash-password -p "your_password"
   ```
2. Update the users.yaml file
3. Ensure `active: true`

### Changes Not Reflecting

Restart Airflow webserver after modifying users.yaml:

```bash
# Standalone mode
# Ctrl+C and restart

# Astro CLI
astro dev restart
```
