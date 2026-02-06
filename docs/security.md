# Security Guide

This guide covers security best practices and considerations for airflow-file-auth-manager.

## Security Model Overview

airflow-file-auth-manager provides:

- **Password Security**: bcrypt hashing with salt
- **Session Security**: JWT tokens with expiration
- **Access Control**: Role-based authorization
- **File-Based Storage**: No external database required

## Password Security

### bcrypt Hashing

Passwords are hashed using bcrypt with:

- **Work Factor**: 12 (2^12 iterations)
- **Salt**: Automatically generated per password
- **Algorithm**: bcrypt (Blowfish-based)

```python
# Password hashing implementation
import bcrypt

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode(), salt).decode()
```

### Password Requirements

While not enforced by the auth manager, we recommend:

- Minimum 12 characters
- Mix of uppercase, lowercase, numbers, symbols
- No dictionary words or common patterns
- Unique passwords for each user

### Password Storage

Passwords are stored as bcrypt hashes in the YAML file:

```yaml
users:
  - username: admin
    password_hash: "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4AwuLvQy1FLq/X5e"
```

The hash format: `$2b$12$<22-char-salt><31-char-hash>`

## Users File Security

### File Permissions

Restrict access to the users file:

```bash
# Owner read/write only
chmod 600 users.yaml

# Set ownership to Airflow user
chown airflow:airflow users.yaml

# Verify permissions
ls -la users.yaml
# -rw------- 1 airflow airflow 1234 Jan 15 10:00 users.yaml
```

### File Location

Store the users file:

- **Do**: Place in `/etc/airflow/` or similar protected directory
- **Do**: Keep outside web-accessible directories
- **Do**: Use absolute paths in configuration
- **Don't**: Store in `/tmp` or world-readable locations
- **Don't**: Store in version control with real passwords

### Backup Considerations

When backing up:

```bash
# Encrypt backups containing users.yaml
tar cz users.yaml | gpg -c > users.yaml.backup.tar.gz.gpg

# Or use encrypted backup solutions
```

## JWT Token Security

### Token Configuration

```ini
[api_auth]
# Shorter expiration for higher security
jwt_expiration_seconds = 3600  # 1 hour
```

### Token Contents

Tokens contain:

```json
{
    "username": "admin",
    "role": "admin",
    "email": "admin@example.com",
    "exp": 1705320000,
    "iat": 1705284000
}
```

Note: Tokens do **not** contain:
- Password hashes
- Sensitive user data

### Cookie Security

For browser sessions:

```python
response.set_cookie(
    key="airflow_jwt",
    value=token,
    max_age=jwt_expiration,
    httponly=False,  # Allows JS access for API calls
    secure=is_secure,  # HTTPS only when available
    samesite="lax",   # CSRF protection
)
```

## Transport Security

### HTTPS Requirement

Always use HTTPS in production:

```nginx
# Nginx configuration
server {
    listen 443 ssl;
    server_name airflow.example.com;

    ssl_certificate /etc/ssl/certs/airflow.crt;
    ssl_certificate_key /etc/ssl/private/airflow.key;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```

### Redirect HTTP to HTTPS

```nginx
server {
    listen 80;
    server_name airflow.example.com;
    return 301 https://$server_name$request_uri;
}
```

## Access Control Best Practices

### Principle of Least Privilege

```yaml
users:
  # Only one admin
  - username: platform_admin
    role: admin

  # Most users are editors or viewers
  - username: data_engineer
    role: editor

  - username: analyst
    role: viewer
```

### Account Separation

- Use individual accounts, not shared credentials
- Create service accounts for automation
- Deactivate accounts when users leave

### Account Lifecycle

```bash
# New employee
python -m airflow_file_auth_manager.cli add-user \
    -f users.yaml -u new.employee -r viewer

# Promotion
python -m airflow_file_auth_manager.cli update-user \
    -f users.yaml -u new.employee -r editor

# Departure (deactivate, don't delete)
python -m airflow_file_auth_manager.cli update-user \
    -f users.yaml -u former.employee --active false
```

## Audit and Monitoring

### Login Monitoring

Monitor Airflow logs for authentication events:

```bash
# Successful logins
grep "User authenticated" /var/log/airflow/webserver.log

# Failed logins
grep "Invalid password" /var/log/airflow/webserver.log
grep "User not found" /var/log/airflow/webserver.log
```

### Suspicious Activity

Watch for:

- Multiple failed login attempts
- Logins from unusual locations/times
- Unexpected role changes
- Access to sensitive resources

### Log Configuration

Enable detailed logging:

```ini
[logging]
logging_level = INFO
```

## Incident Response

### Compromised Password

1. Immediately update the password:
   ```bash
   python -m airflow_file_auth_manager.cli update-user \
       -f users.yaml -u compromised_user -p
   ```

2. Review access logs for unauthorized activity

3. Notify affected users

### Compromised Users File

1. Rotate all passwords immediately
2. Audit all recent changes
3. Review and update file permissions
4. Consider the file contents exposed

### Compromised Token

1. Change user's password (invalidates token)
2. User re-authenticates with new password
3. Monitor for continued unauthorized access

## Comparison with Other Auth Methods

| Aspect | File Auth | FAB Auth | LDAP Auth |
|--------|-----------|----------|-----------|
| Password Storage | bcrypt in YAML | Database | LDAP Server |
| Attack Surface | File system | Database + Web | LDAP Server |
| Credential Recovery | Manual file edit | Web UI / Database | LDAP Admin |
| Audit Trail | Log files | Database logs | LDAP logs |
| Scalability | Low (file locks) | Medium | High |

## Security Checklist

### Deployment

- [ ] HTTPS enabled and enforced
- [ ] Users file has restricted permissions (600)
- [ ] Users file is not in version control
- [ ] Strong passwords for all accounts
- [ ] Only necessary accounts created

### Configuration

- [ ] Appropriate JWT expiration time set
- [ ] Logging enabled for authentication events
- [ ] File path uses absolute path
- [ ] Backup strategy in place

### Operational

- [ ] Regular password rotation
- [ ] Prompt deactivation of departed users
- [ ] Periodic review of user access
- [ ] Monitoring for suspicious activity

## Known Limitations

### No Built-in Features

airflow-file-auth-manager does not provide:

- Password complexity enforcement
- Account lockout after failed attempts
- Multi-factor authentication (MFA)
- Session management (force logout)
- Password expiration

### Mitigation Strategies

For environments requiring these features:

1. **Password Policy**: Enforce at organization level
2. **Account Lockout**: Implement via reverse proxy (fail2ban)
3. **MFA**: Use a reverse proxy with MFA (oauth2-proxy)
4. **Session Management**: Reduce JWT expiration time
5. **Password Expiration**: Manual policy enforcement

## Reporting Security Issues

If you discover a security vulnerability:

1. Do not open a public issue
2. Email security concerns privately
3. Provide detailed reproduction steps
4. Allow time for a fix before disclosure
