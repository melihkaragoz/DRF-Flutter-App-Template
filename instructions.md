Here’s a single, precise prompt you can paste into Cursor (Claude 4 Sonnet) to scaffold a minimal, **easy-to-understand** template:

---

**Prompt to Claude 4 Sonnet**

You are my senior engineer. Scaffold a **minimal, crystal-clear** template that I can run immediately:

**Goal**
Create a tiny, production-minded-but-dev-simple stack:
- **Backend**: Django + DRF + Simple JWT
- **DB**: PostgreSQL
- **Containerization**: Docker + Docker Compose (dev mode)
- **Frontend**: Flutter (very small app) consuming the API over JWT
- **Scope**: Only 3 flows:
  1) **Register user** (username, email optional, password)
  2) **JWT login** (access + refresh)
  3) **Profile** endpoint returning current user info (id, username, email)

**Non-negotiable simplicity**
- Keep things **small** and **boring**. No over-engineering.
- Only the essentials. Avoid extra libraries beyond what is stated.
- **Dev ergonomics**: I don’t want to constantly rebuild containers. Use **docker-compose with volume mounts** so code changes reflect immediately (Django’s dev autoreload). No extra “file watch” gizmos; the mount is enough.
- Clear, step-by-step instructions. No skipped steps. No magic.

---

## Deliverables (single Markdown answer)

### 1) File tree
Show a concise repo tree like:
```
/backend/...
/frontend/...
docker-compose.yml
README.md
```

### 2) Backend (Django + DRF + SimpleJWT)
- A **Dockerized** Django project under `backend/` with:
  - `Dockerfile` (Python 3.12 slim preferred)
  - `requirements.txt` containing: `Django`, `djangorestframework`, `djangorestframework-simplejwt`, `psycopg2-binary`, `django-environ` (only these unless truly necessary)
  - `manage.py`, project package (e.g., `config/`), and a single app `users/`
  - `settings.py`:
    - `INSTALLED_APPS`: `rest_framework`, `rest_framework_simplejwt`, the `users` app
    - DB from env vars (host, name, user, pass, port), using `django-environ`
    - `REST_FRAMEWORK` default auth set to **JWT** (SimpleJWT)
    - `ALLOWED_HOSTS=['*']` for dev
    - `TIME_ZONE='UTC'`, `USE_TZ=True`
    - **No CORS config** unless absolutely required (native mobile doesn’t need it)
  - `urls.py` with three groups:
    - `/api/auth/jwt/create/`, `/api/auth/jwt/refresh/`, `/api/auth/jwt/verify/` (SimpleJWT)
    - `/api/users/register/` (POST): create a user; password hashed; returns `{id, username, email}`
    - `/api/users/me/` (GET, auth required): returns `{id, username, email}`
  - `users/serializers.py`, `users/views.py`, `users/urls.py` (tiny, clear)
- **Docker Compose** at project root:
  - Services: `backend` (Django) and `db` (Postgres)
  - `backend`:
    - build from `backend/Dockerfile`
    - mounts `./backend:/app` for autoreload
    - command `python manage.py migrate && python manage.py runserver 0.0.0.0:8000`
    - env vars via `.env` at root (include example values)
    - depends_on db (with a simple Postgres healthcheck)
  - `db`:
    - image: `postgres:16`
    - env: POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
    - volume for data persistence
    - healthcheck
- Include a tiny `entrypoint.sh` **only if** you find it necessary to wait for DB; otherwise rely on `depends_on` + healthcheck. Keep it simple.

### 3) Frontend (Flutter)
Under `frontend/`:
- Minimal Flutter app with **two screens**: `LoginPage` and `ProfilePage`
- **Packages**: only `http` and `flutter_secure_storage`
- A tiny `ApiClient` that:
  - `register(username, password, email?)`
  - `login(username, password)` → stores `access` & `refresh` in secure storage
  - `getProfile()` using `Authorization: Bearer <access>`
  - (Optional but nice): if a 401 occurs, try refresh once via `/auth/jwt/refresh/`, then retry; if fails, log out. Keep this logic **very small** or skip if it complicates.
- Base URL logic:
  - If `Platform.isAndroid`: `http://10.0.2.2:8000`
  - Else: `http://127.0.0.1:8000`
- Android: add INTERNET permission
- No fancy state management—use a simple `StatefulWidget` or minimal `ChangeNotifier` if you must. Keep it straightforward.

### 4) Exact file contents
For **every file** that matters, print the **full content** in separate code blocks with the correct paths at the top like:
```txt
# backend/requirements.txt
<content>
```
Do this for:
- `docker-compose.yml`
- `.env.example`
- `backend/Dockerfile`
- `backend/requirements.txt`
- `backend/manage.py`
- `backend/config/__init__.py`
- `backend/config/settings.py`
- `backend/config/urls.py`
- `backend/config/asgi.py` and `wsgi.py` (standard minimal)
- `backend/users/apps.py`
- `backend/users/models.py` (use Django default `User`; don’t customize unless required)
- `backend/users/serializers.py`
- `backend/users/views.py`
- `backend/users/urls.py`
- (Only if used) `backend/entrypoint.sh` (remember to `chmod +x` mention)
- `frontend/pubspec.yaml`
- `frontend/lib/main.dart` (router optional; keep it small)
- `frontend/lib/api_client.dart`
- `frontend/lib/login_page.dart`
- `frontend/lib/profile_page.dart`
- `frontend/android/app/src/main/AndroidManifest.xml` (permission line)
  
Avoid extraneous files. No tests for now.

### 5) Commands & runbook (end-to-end)
Add a concise **“How to run”** section the user can copy-paste:
1. `cp .env.example .env` and fill values
2. `docker compose up --build`
3. In another terminal: `cd frontend` then `flutter pub get` then `flutter run`
4. **Register** via app or via curl:
   - `curl -X POST http://127.0.0.1:8000/api/users/register/ -H "Content-Type: application/json" -d '{"username":"demo","password":"demo123","email":"d@d.com"}'`
5. **Login** in the app, then open **Profile** to see JSON output.

Include a tiny ASCII diagram of the token flow:
```
[Flutter] --register--> [DRF]
[Flutter] --login--> {access, refresh}
[Flutter] --GET /users/me (Bearer access)--> [DRF] -> user JSON
```

### 6) Design constraints recap
- Minimal dependencies (listed above). No Celery, no Nginx, no gunicorn for dev.
- Dev autoreload relies on Django + mounted volume.
- Clear comments only where helpful; avoid long essays.
- Everything should be **self-explanatory**; there must be **zero ambiguous steps**.

### 7) Acceptance checklist
- I can `docker compose up` and see Django at `:8000`
- I can register → login → fetch profile from the Flutter app
- Code is short, readable, and logically grouped
- No missing file, no missing instruction

Now, produce the **complete template** in one Markdown answer with the exact file contents as requested.
