# Clinic Management Backend — FastAPI

Production-oriented backend for the clinic web application.

## Correct onboarding flow

1. `GET /api/v1/setup/status`
2. If setup is required, `POST /api/v1/setup/register-clinic`
3. The transaction creates:
   - clinic
   - first user
   - `ADMIN` clinic membership
   - clinic settings
4. Admin logs in.
5. Admin creates doctors and Front Desk users.
6. Admin assigns doctors/staff to one or more clinics.
7. Admin configures doctor schedules and leave.
8. Patients, appointments, billing, reminders and reports become available.

The old `Practice Manager` / `manager` role is intentionally NOT implemented.
The administrative role is `ADMIN`.

## Stack

- FastAPI
- SQLAlchemy 2.x
- Alembic
- Pydantic v2
- JWT access/refresh tokens
- Argon2 password hashing
- PostgreSQL in production
- SQLite supported for quick local development

## Run

### 1. Create environment

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Database

For PostgreSQL set:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/clinic_db
```

SQLite fallback:

```env
DATABASE_URL=sqlite:///./clinic.db
```

### 3. Start

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

Swagger:

`http://127.0.0.1:8000/docs`

Health:

`GET /health`

## Security notes

- Never store passwords or PINs in plain text.
- The frontend is NOT trusted for authorization.
- Every clinic-scoped endpoint verifies clinic membership.
- Doctors are restricted to their assigned clinics and their own appointments.
- Financial records use transactions and audit logging.
- Production should use HTTPS, a strong JWT secret, PostgreSQL, secure refresh-token storage and a real message provider.

## Important implementation note

The prototype used browser-local storage and demo PINs. This backend replaces that mechanism with server-side authentication and SQL persistence while preserving the application's functional areas: dashboard, patients, appointments, billing, reminders, reports, clinics, doctors, schedules and leave.
