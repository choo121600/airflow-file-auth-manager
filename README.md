# airflow-file-auth-manager

YAML 파일 기반 경량 Auth Manager for Apache Airflow 3.x

## 개요

LDAP나 외부 인증 서비스 없이 1~3명 소규모 팀을 위한 간단한 파일 기반 인증 시스템입니다.

### 주요 기능

- **bcrypt 해시 비밀번호**: 안전한 비밀번호 저장
- **3단계 역할 체계**: Admin, Editor, Viewer
- **JWT 토큰 인증**: 세션 관리
- **YAML 파일 기반**: 간단한 사용자 관리

## 설치

```bash
pip install airflow-file-auth-manager
```

또는 소스에서 설치:

```bash
git clone https://github.com/yeonguk/airflow-file-auth-manager.git
cd airflow-file-auth-manager
pip install -e .
```

## 설정

### 1. 사용자 파일 생성

```bash
# 초기화 및 admin 사용자 생성
python -m airflow_file_auth_manager.cli init -f /path/to/users.yaml

# 또는 수동으로 사용자 추가
python -m airflow_file_auth_manager.cli add-user \
    -f /path/to/users.yaml \
    -u admin \
    -r admin \
    -e admin@example.com
```

### 2. Airflow 설정

`airflow.cfg`:

```ini
[core]
auth_manager = airflow_file_auth_manager.FileAuthManager

[file_auth_manager]
users_file = /path/to/users.yaml
```

또는 환경 변수:

```bash
export AIRFLOW__CORE__AUTH_MANAGER=airflow_file_auth_manager.FileAuthManager
export AIRFLOW_FILE_AUTH_USERS_FILE=/path/to/users.yaml
```

## 역할 체계

| 역할 | 권한 |
|------|------|
| **Admin** | 전체 권한 (Connection, Variable, Config 수정 포함) |
| **Editor** | DAG 실행/관리, 읽기 전체 |
| **Viewer** | 읽기 전용 |

### 상세 권한

| 리소스 | Viewer | Editor | Admin |
|--------|--------|--------|-------|
| DAG 조회 | ✅ | ✅ | ✅ |
| DAG 실행/관리 | ❌ | ✅ | ✅ |
| Connection 조회 | ✅ | ✅ | ✅ |
| Connection 수정 | ❌ | ❌ | ✅ |
| Variable 조회 | ✅ | ✅ | ✅ |
| Variable 수정 | ❌ | ❌ | ✅ |
| Pool 조회 | ✅ | ✅ | ✅ |
| Pool 수정 | ❌ | ❌ | ✅ |
| Configuration | ✅ (읽기) | ✅ (읽기) | ✅ |

## 사용자 파일 형식

`users.yaml`:

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

  - username: viewer
    password_hash: "$2b$12$..."
    role: viewer
    email: viewer@example.com
    active: true
```

## CLI 명령어

### 사용자 추가

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

### 사용자 수정

```bash
python -m airflow_file_auth_manager.cli update-user \
    -f users.yaml \
    -u username \
    [-p]  # 비밀번호 변경 (대화형 입력)
    [-r role] \
    [-e email] \
    [--active true|false]
```

### 사용자 삭제

```bash
python -m airflow_file_auth_manager.cli delete-user \
    -f users.yaml \
    -u username \
    [-y]  # 확인 건너뛰기
```

### 사용자 목록

```bash
python -m airflow_file_auth_manager.cli list-users -f users.yaml
```

### 비밀번호 해시 생성

```bash
python -m airflow_file_auth_manager.cli hash-password [-p password]
```

### 초기화

```bash
python -m airflow_file_auth_manager.cli init \
    -f users.yaml \
    [-p admin_password] \
    [-e admin@email.com] \
    [--force]
```

## API 인증

### 토큰 발급

```bash
curl -X POST http://localhost:8080/auth/file/token \
    -H "Content-Type: application/json" \
    -d '{"username": "admin", "password": "secret"}'
```

응답:

```json
{
    "access_token": "eyJ...",
    "token_type": "Bearer",
    "expires_in": 36000
}
```

### API 요청

```bash
curl http://localhost:8080/api/v1/dags \
    -H "Authorization: Bearer eyJ..."
```

## 개발

### 테스트 실행

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

### 로컬 테스트 (Astro CLI)

```bash
# report-airflow 프로젝트에서
pip install -e ../airflow-file-auth-manager
astro dev start
```

## 보안 고려사항

- 사용자 파일(`users.yaml`)은 적절한 권한으로 보호하세요 (`chmod 600`)
- 프로덕션에서는 강력한 비밀번호를 사용하세요
- JWT 토큰 만료 시간을 적절히 설정하세요

## 라이선스

Apache License 2.0
