# Plan: Merge mess_auth + mess_user into a single service

## Why

Both services manage the same entity (users) and mess_user already depends on
mess_auth via HTTP calls during registration. Keeping them separate adds:

- An extra database, container, and deployment unit
- Inter-service HTTP calls that could be direct function calls
- Duplicated user records across two databases
- Extra Kong routing complexity

The merged service will be called **mess-user** and will own everything
user-related: registration, login, token management, profile queries.

---

## Current state (for reference)

| | mess_auth | mess_user |
|---|---|---|
| DB tables | `users` (user_id, username, hashed_password), `refresh_tokens` | `users` (id, username, is_active, created_at) |
| Endpoints | POST login, POST refresh-token, POST logout, POST /users (internal) | POST /users (register), GET /users (search), POST /users/batch-query |
| Kong routes | login-service (public) | user-service (JWT), user-service-public |
| Docker | auth + auth_db containers | user + user_db containers |

---

## Steps

### Step 1 - Merge database schemas

Combine both `users` tables into one and keep `refresh_tokens`.

**Merged `users` table:**
```
user_id     VARCHAR(32)  PK
username    VARCHAR(150) UNIQUE NOT NULL
hashed_password VARCHAR(72) NOT NULL
is_active   BOOLEAN      NOT NULL DEFAULT TRUE
created_at  VARCHAR(32)  NOT NULL
```

**What to do:**
- Add `hashed_password` column to mess_user's User model
- Add `is_active` and `created_at` columns to the schema (already in mess_user)
- Copy the `RefreshToken` model from mess_auth into mess_user/models/
- Write a new Alembic migration in mess_user that adds the missing columns
- Unify the primary key name to `user_id` (mess_auth uses `user_id`, mess_user uses `id`)

---

### Step 2 - Merge application code into mess_user

Bring auth logic (password hashing, JWT, token management) into the mess_user
service.

**What to do:**
- Copy `mess_auth/utils.py` -> `mess_user/utils.py` (password + JWT helpers)
- Copy `mess_auth/constants.py` content (ALGORITHM) into `mess_user/constants.py`
- Merge repository functions: add auth's `refresh_token_exists`,
  `create_refresh_token`, `update_refresh_token`, `delete_refresh_token`,
  and password-related user queries into mess_user's repository
- Merge settings: add `jwt_secret_key`, `jwt_kid`,
  `access_token_expire_minutes`, `refresh_token_expire_minutes` to
  mess_user/settings.py. Remove `auth_url` (no longer needed)
- Add auth dependencies to mess_user's `requirements.txt`:
  `python-jose[cryptography]`, `passlib[bcrypt]`
- Remove `requests`, `httpx`, `result` from requirements (no more inter-service
  calls)

---

### Step 3 - Merge endpoints into mess_user/main.py

Bring auth endpoints into the user service and refactor registration to be a
direct function call instead of an HTTP call.

**Final endpoint list:**

| Endpoint | Method | Auth | Source |
|---|---|---|---|
| `/api/user/v1/users` | POST | Public | was mess_user (register) |
| `/api/user/v1/users` | GET | JWT | was mess_user (search) |
| `/api/user/v1/users/batch-query` | POST | JWT | was mess_user (batch) |
| `/api/auth/v1/login` | POST | Public | from mess_auth |
| `/api/auth/v1/refresh-token` | POST | Public | from mess_auth |
| `/api/auth/v1/logout` | POST | Public | from mess_auth |

**What to do:**
- Add login, refresh-token, logout endpoints to mess_user/main.py
  (adapt from mess_auth/main.py, use merged repository)
- Refactor the registration endpoint: instead of HTTP-calling auth service,
  directly hash the password and store in the same DB row
- Remove `mess_user/helpers/user.py` (`create_user_in_auth` no longer needed)
- Keep `get_current_active_user` helper (move to deps or helpers)

---

### Step 4 - Update Kong configuration

Point all routes to the single `user` service and remove the `auth` service
references.

**What to do in `mess/config/kong.yaml`:**
- Change `login-service` host from `http://auth:80` to `http://user:80`
- Remove the separate `auth` service definition
- Keep all existing route paths unchanged (clients see no difference)

---

### Step 5 - Update docker-compose

Remove auth container and its database.

**What to do in `mess/docker-compose.yml`:**
- Remove `auth` service
- Remove `auth_db` service
- Remove `auth_db` volume
- Update `user` service env to include JWT settings (previously in auth_prod.env)
- Merge auth_prod.env settings into user_prod.env, delete auth_prod.env

---

### Step 6 - Clean up and delete mess-auth

- Delete the entire `mess-auth/` directory
- Remove any references to `auth` service in remaining config files
- Update dev.env files for local development
- Run the full stack and verify all endpoints work

---

## Migration strategy (existing data)

If there is production data:
1. Create the new migration that adds `hashed_password` to mess_user's users
   table
2. Write a one-time data migration script that copies `hashed_password` from
   auth_db into user_db for matching user_ids
3. Copy `refresh_tokens` table data into user_db
4. Deploy merged service
5. Decommission auth_db after verification

If no production data: just run the new migrations fresh.

---

## Execution order

```
Step 1 (schema)  -->  Step 2 (code)  -->  Step 3 (endpoints)
                                              |
                                              v
                      Step 6 (cleanup) <-- Step 5 (docker) <-- Step 4 (kong)
```

Steps 1-3 are the core merge. Steps 4-5 are infrastructure. Step 6 is cleanup.
Each step should be independently testable before moving to the next.
