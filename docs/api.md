# API Authentication Guide

This guide covers how to authenticate with the Airflow REST API using airflow-file-auth-manager.

## Overview

airflow-file-auth-manager uses JWT (JSON Web Tokens) for API authentication. The workflow is:

1. Obtain a JWT token by authenticating with username/password
2. Include the token in subsequent API requests
3. Token expires after configured duration (default: 10 hours)

## Authentication Endpoints

### Login Page

**GET** `/auth/file/login`

Displays the login form for browser-based authentication.

Query Parameters:
- `next` - URL to redirect to after successful login

Example:
```
http://localhost:8080/auth/file/login?next=/dags
```

### Obtain Token

**POST** `/auth/file/token`

Authenticates user and returns a JWT token.

#### JSON Request

```bash
curl -X POST http://localhost:8080/auth/file/token \
    -H "Content-Type: application/json" \
    -d '{"username": "admin", "password": "your_password"}'
```

#### Form Request

```bash
curl -X POST http://localhost:8080/auth/file/token \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=admin&password=your_password"
```

#### Success Response

```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 36000
}
```

#### Error Responses

**400 Bad Request** - Missing credentials:
```json
{
    "error": "Username and password required"
}
```

**401 Unauthorized** - Invalid credentials:
```json
{
    "error": "Invalid username or password"
}
```

### Logout

**GET** `/auth/file/logout`

Clears the authentication cookie and redirects to login page.

```bash
curl http://localhost:8080/auth/file/logout
```

## Using the Token

### Authorization Header

Include the token in the `Authorization` header:

```bash
curl http://localhost:8080/api/v1/dags \
    -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Cookie (Browser)

For browser-based access, the token is automatically stored as a cookie named `airflow_jwt`.

## API Request Examples

### List DAGs

```bash
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl -s http://localhost:8080/api/v1/dags \
    -H "Authorization: Bearer $TOKEN" | jq
```

### Trigger DAG Run

```bash
curl -X POST http://localhost:8080/api/v1/dags/my_dag/dagRuns \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "logical_date": "2024-01-15T10:00:00Z",
        "conf": {"key": "value"}
    }'
```

### Get DAG Run Status

```bash
curl http://localhost:8080/api/v1/dags/my_dag/dagRuns/my_run_id \
    -H "Authorization: Bearer $TOKEN"
```

### List Connections

```bash
curl http://localhost:8080/api/v1/connections \
    -H "Authorization: Bearer $TOKEN"
```

### Create Variable (Admin only)

```bash
curl -X POST http://localhost:8080/api/v1/variables \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "key": "my_variable",
        "value": "my_value"
    }'
```

## Python Client Examples

### Using requests

```python
import requests

BASE_URL = "http://localhost:8080"

# Authenticate
response = requests.post(
    f"{BASE_URL}/auth/file/token",
    json={"username": "admin", "password": "your_password"}
)
token = response.json()["access_token"]

# Create session with auth header
session = requests.Session()
session.headers.update({"Authorization": f"Bearer {token}"})

# List DAGs
dags = session.get(f"{BASE_URL}/api/v1/dags").json()
for dag in dags["dags"]:
    print(f"{dag['dag_id']}: {dag['is_paused']}")

# Trigger DAG
session.post(
    f"{BASE_URL}/api/v1/dags/my_dag/dagRuns",
    json={"logical_date": "2024-01-15T10:00:00Z"}
)
```

### Using httpx (Async)

```python
import httpx
import asyncio

async def main():
    async with httpx.AsyncClient(base_url="http://localhost:8080") as client:
        # Authenticate
        response = await client.post(
            "/auth/file/token",
            json={"username": "admin", "password": "your_password"}
        )
        token = response.json()["access_token"]

        # Set auth header
        client.headers.update({"Authorization": f"Bearer {token}"})

        # List DAGs
        dags = await client.get("/api/v1/dags")
        print(dags.json())

asyncio.run(main())
```

### Reusable Auth Client

```python
class AirflowClient:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url
        self.session = requests.Session()
        self._authenticate(username, password)

    def _authenticate(self, username: str, password: str):
        response = self.session.post(
            f"{self.base_url}/auth/file/token",
            json={"username": username, "password": password}
        )
        response.raise_for_status()
        token = response.json()["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def list_dags(self):
        return self.session.get(f"{self.base_url}/api/v1/dags").json()

    def trigger_dag(self, dag_id: str, conf: dict = None):
        return self.session.post(
            f"{self.base_url}/api/v1/dags/{dag_id}/dagRuns",
            json={"conf": conf or {}}
        ).json()

# Usage
client = AirflowClient(
    "http://localhost:8080",
    "admin",
    "your_password"
)
print(client.list_dags())
```

## Token Management

### Token Expiration

Tokens expire after `jwt_expiration_seconds` (default: 36000 = 10 hours).

Check expiration in token payload:

```python
import jwt
import datetime

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
# Note: This decodes without verification - for inspection only
payload = jwt.decode(token, options={"verify_signature": False})
exp = datetime.datetime.fromtimestamp(payload["exp"])
print(f"Token expires at: {exp}")
```

### Token Refresh

There's no refresh token endpoint. When a token expires:

1. Re-authenticate with username/password
2. Get a new token

### Token Payload

The JWT payload contains:

```json
{
    "username": "admin",
    "role": "admin",
    "email": "admin@example.com",
    "first_name": "Admin",
    "last_name": "User",
    "exp": 1705320000,
    "iat": 1705284000
}
```

## Error Handling

### 401 Unauthorized

Token is missing, invalid, or expired:

```json
{
    "detail": "Not authenticated"
}
```

Solution: Re-authenticate and get a new token.

### 403 Forbidden

User doesn't have permission for the action:

```json
{
    "detail": "Access denied"
}
```

Solution: Use an account with appropriate role.

### Token Validation Errors

```python
def make_request(session, url):
    response = session.get(url)

    if response.status_code == 401:
        # Re-authenticate
        token = authenticate()
        session.headers.update({"Authorization": f"Bearer {token}"})
        response = session.get(url)

    if response.status_code == 403:
        raise PermissionError("Insufficient permissions")

    response.raise_for_status()
    return response.json()
```

## Security Considerations

### Token Storage

- Never store tokens in code or version control
- Use environment variables for automation
- Tokens are sensitive - treat like passwords

### HTTPS

Always use HTTPS in production:

```python
# Good
client = AirflowClient("https://airflow.mycompany.com", ...)

# Bad - tokens sent in plain text
client = AirflowClient("http://airflow.mycompany.com", ...)
```

### Token Exposure

If a token is exposed:

1. Change the user's password immediately
2. Existing tokens become invalid
3. Re-authenticate with new password

## Rate Limiting

airflow-file-auth-manager doesn't implement rate limiting. Consider:

- Using a reverse proxy (nginx, traefik) for rate limiting
- Implementing application-level rate limiting
- Monitoring for unusual API activity
