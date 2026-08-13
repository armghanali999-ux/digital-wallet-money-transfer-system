# Digital Wallet & Money Transfer System

A Django 5.2 LTS, Django REST Framework, and MySQL web application with explicit service/repository separation, session-authenticated customer pages, JWT APIs, auditable ledger entries, and protected administrator operations.

## Requirements

- Python 3.14
- MySQL 8.0+
- Existing approved environment: `C:\Users\ghori\Documents\Codex\DigitalWallet\Packages`
- Exact Python dependencies: `requirements.txt`

Do not create another virtual environment in this repository. Secrets belong only in `.env`, which is ignored by Git.

## Architecture

```text
Web/API views -> services/business rules -> repositories/data access -> Django ORM -> MySQL
```

- Views and serializers validate transport shapes and delegate work.
- `wallets/services.py` owns business rules, authorization-aware operations, atomic transaction boundaries, idempotency coordination, state transitions, and ledger creation.
- Repository modules own reusable queries, deterministic row locking, daily aggregates, idempotency locking, and transaction-reference allocation.
- Models define entities, indexes, uniqueness, precision, and non-negative/positive database constraints.
- Domain exceptions are mapped centrally to consistent safe JSON errors.
- Generic wallet APIs and Django admin cannot edit balances or protected wallet state.

## Database setup

Run as a MySQL administrator, replacing the password privately:

```sql
CREATE DATABASE IF NOT EXISTS digital_wallet
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS test_digital_wallet
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'digital_wallet_app'@'localhost'
  IDENTIFIED BY 'REPLACE_WITH_A_PRIVATE_PASSWORD';
GRANT ALL PRIVILEGES ON digital_wallet.* TO 'digital_wallet_app'@'localhost';
GRANT ALL PRIVILEGES ON test_digital_wallet.* TO 'digital_wallet_app'@'localhost';
FLUSH PRIVILEGES;
```

Copy `.env.example` to `.env`, generate a long random Django key, and enter the matching private database password. Never commit or share `.env`.

## Run

From PowerShell in the project directory:

```powershell
$python = 'C:\Users\ghori\Documents\Codex\DigitalWallet\Packages\Scripts\python.exe'
& $python manage.py migrate
& $python manage.py createsuperuser
& $python manage.py runserver
```

Open `http://127.0.0.1:8000/`. The purpose-built operations interface is at `/administration/`; the secondary maintenance admin is at `/django-admin/`.

## Railway deployment from GitHub

Railway deploys this project directly from the same GitHub repository. The repository root contains `railway.json`, so no Dockerfile, monorepo path, or relocated source tree is required.

1. In Railway, choose **New Project → Deploy from GitHub repo** and select `armghanali999-ux/digital-wallet-money-transfer-system`.
2. Add a Railway MySQL service to the same project.
3. Generate a public domain for the application service.
4. Add the application variables listed below. Reference the linked service rather than copying its credentials.
5. Redeploy the application. The configured start command applies migrations before starting the production WSGI server.

Required application variables:

```text
DJANGO_SECRET_KEY=<a long, unique random value>
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=${{RAILWAY_PUBLIC_DOMAIN}}
DJANGO_CSRF_TRUSTED_ORIGINS=https://${{RAILWAY_PUBLIC_DOMAIN}}
DJANGO_SECURE_COOKIES=true
DJANGO_SECURE_SSL_REDIRECT=false
DJANGO_TIME_ZONE=Asia/Karachi
DJANGO_LOG_LEVEL=INFO
DATABASE_URL=${{MySQL.MYSQL_URL}}
```

`PORT` is injected automatically by Railway and must not be hard-coded. `DATABASE_URL` is parsed as a MySQL URL, including percent-encoded usernames/passwords. The individual `MYSQL_*` variables remain supported for local development.

Railway settings:

```text
Root directory: /
Builder: Nixpacks
Build command: python manage.py collectstatic --noinput
Start command: python manage.py migrate --noinput && waitress-serve --listen=0.0.0.0:$PORT config.wsgi:application
Health-check path: /health/
Health-check timeout: 120 seconds
```

The production start command binds to `0.0.0.0` and Railway's supplied port. WhiteNoise serves versioned static assets. The application database is the linked Railway MySQL service; local database files and credentials are never committed.

To run migrations manually from a Railway service shell when needed:

```text
python manage.py migrate --noinput
```

## Tests

Tests use the isolated MySQL database named by `MYSQL_TEST_DATABASE` (default `test_digital_wallet`):

```powershell
& $python -m pip check
& $python manage.py check --database default
& $python manage.py makemigrations --check --dry-run
& $python -m pytest
```

MySQL—not SQLite—is used so database constraints, transactions, and locking can be tested meaningfully.

## Safe demonstration data

With local `DEBUG=True`, create demo customer/admin accounts and zero-balance USD/PKR customer wallets:

```powershell
& $python manage.py seed_demo
```

The command generates random one-time local passwords and prints them once; no password is embedded in source. Re-running preserves existing passwords. Use `seed_demo --reset-passwords` only when replacement demo passwords are wanted. The command refuses to run when `DEBUG=False`.

## API conventions

Authenticated APIs accept JWT bearer tokens. Financial POST operations also require an `Idempotency-Key` header. Identical actor/operation/key/payload retries return the stored result; changed payloads are rejected. Keys are protected by a database unique constraint and locked transactionally.

Success response:

```json
{"success": true, "data": {"reference": "TXN-20260812-000001", "status": "COMPLETED"}}
```

Domain error response:

```json
{"success": false, "error": {"code": "insufficient_funds", "message": "Insufficient funds."}}
```

### Authentication

- `POST /api/auth/register/`
- `POST /api/auth/token/`
- `POST /api/auth/token/refresh/`

### Customer wallets and money operations

- `GET|POST /api/wallets/`
- `GET /api/wallets/{id}/`
- `POST /api/wallet/deposit/`
- `POST /api/wallet/withdraw/`
- `POST /api/wallet/transfer/`
- `GET /api/wallet/transactions/`
- `GET /api/wallet/transactions/{reference}/`

Deposit example:

```http
POST /api/wallet/deposit/
Authorization: Bearer ACCESS_TOKEN
Idempotency-Key: 2d8da280-7aad-48cb-bf4a-30ad83d9aa48
Content-Type: application/json

{"wallet_id": 1, "amount": "100.0000", "currency": "USD", "description": "Initial funds"}
```

Transaction filters are `type`, `status`, `start_date`, `end_date`, `min_amount`, `max_amount`, and partial/exact `reference`. Results use stable newest-first ordering and page-number pagination.

### Administrator API

- `GET /api/admin/users/`
- `GET /api/admin/wallets/?q=email`
- `POST /api/admin/wallets/{id}/freeze/`
- `POST /api/admin/wallets/{id}/unfreeze/`
- `POST /api/admin/wallets/{id}/adjust-balance/`

Freeze/unfreeze requires `{"reason": "..."}`. Balance adjustment requires a signed Decimal amount, mandatory reason, and `Idempotency-Key`. The service prevents negative balances and creates a BALANCE_ADJUSTMENT transaction, ledger entry, and administrative audit record.

Administrators can filter all transactions—including `status=FAILED`—through the transaction API/admin, inspect safe failure fields and related wallets, and review administrative audits. Password hashes and tokens are not exposed by API serializers.

## Submission demonstration

1. Register Alice and Bob and create one USD wallet for each.
2. Deposit into Alice's wallet, withdraw a smaller amount, and inspect both receipts.
3. Transfer from Alice to Bob through the confirmation page; verify both balances and both ledger legs.
4. Repeat the API request with its original `Idempotency-Key`; verify no second balance change occurs.
5. As an administrator, freeze Bob's wallet and verify money operations fail while history remains visible.
6. Unfreeze it, make a reasoned balance adjustment, and inspect the audit history.
7. Exercise every transaction-history filter.

The automated equivalent is `test_complete_customer_and_administrator_api_demonstration`. The complete 18-section evidence map is in `docs/REQUIREMENT_TRACEABILITY.md`.

## Financial behavior

- Wallet and transaction amounts use `Decimal(19,4)`, never floats.
- Supported currencies and deposit/withdrawal/transfer single/daily limits are stored in `FinancialConfiguration`; defaults are seeded in the database.
- Wallet balance has a database non-negative constraint.
- One ACTIVE wallet per owner/currency is enforced through a nullable active-currency marker and database uniqueness.
- FROZEN/CLOSED wallets remain visible but cannot move money.
- Transfers lock both wallet rows by ascending ID and commit debit, credit, transaction, and two ledger entries together.
- Withdrawals lock the wallet before daily-limit and balance checks.
- Human-readable references use a MySQL atomic daily counter and a unique transaction constraint. Gaps may occur after rollbacks; collisions cannot commit.
- Valid state transitions are PENDING to COMPLETED, FAILED, or CANCELLED only.
- Expected business failures are recorded after the money transaction rolls back, with safe failure code/reason fields and actor-scoped idempotency; identical failed retries do not create duplicate failure records.

## Web interface

Customer pages include registration, login/logout, dashboard, wallet creation, deposit, withdrawal, a true two-step transfer confirmation, receipts, complete transaction history filters/pagination, and details. Django sessions and CSRF protection are used. Bootstrap provides responsive, keyboard-accessible baseline styling.

The application also provides six account-persisted themes: Emerald Finance (default), Navy Teal Fintech, Indigo Professional, Premium Black Gold, Classic Blue, and Dark Mode. Users select a theme from `/settings/`; JavaScript previews and saves it immediately, while the database and session preserve it across requests and future logins. All application theming is centralized in `accounts/themes.py` and `static/css/theme.css` using CSS variables.

The purpose-built administrator pages provide user and wallet search, wallet details, POST-only freeze/unfreeze controls, controlled balance adjustments, failed-transaction investigation, and audit history. The customized Django admin remains a secondary maintenance tool. Direct wallet balance/status changes are disabled; controlled changes use service-layer operations.

## Security notes and current limitations

- DEBUG, hosts, cookies, logging, database access, and keys are environment-driven.
- DRF defaults to authenticated access; only registration, token, and health routes are public.
- Logs and responses must not contain passwords, JWTs, database credentials, or internal tracebacks.
- No currency conversion, payment gateway, React, Redis, Celery, Docker, or deployment configuration is included.
- Phase 3 completed the 18-section PDF audit, acceptance workflow and safe demo tooling. The final verified test count is recorded in `PHASE_CHECKLIST.md`.
