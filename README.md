# URL Shortener API

A production-style URL shortener built with FastAPI and SQLAlchemy 2.0, backed by PostgreSQL (Neon). Phase 1: fully anonymous — create a short link, redirect through it, track clicks. No user accounts yet (see Roadmap).

## Stack

- **FastAPI** — web framework
- **SQLAlchemy 2.0** — ORM
- **PostgreSQL (Neon)** — database
- **Alembic** — schema migrations
- **Pydantic v2** — request/response validation
- **slowapi** — rate limiting (Redis-backed via Upstash)
- **pytest** — test suite (dev-only)

## Endpoints

| Method | Path        | Description                                             |
|--------|-------------|-----------------------------------------------------------|
| POST   | `/shorten`  | Create a short link for a given long URL                  |
| GET    | `/{code}`   | Redirect (302) to the long URL, incrementing click count   |
| GET    | `/health`   | Health check                                                |

Interactive docs at `/docs` once the server is running.

## Design notes

- **Short links are immutable.** Once created, a code always points to the same destination — no update endpoint. Simpler, matches how bit.ly/TinyURL behave, and sidesteps the update race condition entirely.
- **Short code generation is collision-safe under concurrency.** Codes are random base62 strings. Rather than checking for existence before inserting (a check-then-insert race, however unlikely at 62^7 possibilities), the DB's unique constraint on `short_code` is the real safety net — a collision raises `IntegrityError`, which triggers a retry with a fresh code (up to 5 attempts).
- **Click counting is atomic.** `GET /{code}` uses a single `UPDATE ... SET click_count = click_count + 1 ... RETURNING long_url` statement, so concurrent clicks on the same link can't produce lost updates the way a separate read-then-write would.
- **302, not 301, redirects.** A 301 would get cached by browsers/CDNs, meaning repeat clicks skip this server entirely — fast, but breaks click tracking. 302 ensures every click is recorded.
- **Rate limiting is asymmetric.** `POST /shorten` is capped at 10/minute per IP (this is the endpoint someone could abuse to spam links). `GET /{code}` is capped much looser (60/minute) since it's meant to absorb real traffic, including bots/link-preview crawlers unwrapping links legitimately.
- **Rate limit storage is Redis (Upstash), not in-memory.** In-memory counters are only correct with exactly one running process; Redis makes the limit correct across multiple workers/instances.
- **The client IP used for rate limiting is proxy-aware and off by default.** `TRUSTED_PROXY_HOPS` (default `0`) controls whether `X-Forwarded-For` is trusted at all. At `0`, the header is ignored entirely and the raw socket IP is used — safe for local dev, where trusting the header would let anyone spoof their rate-limit identity. In production behind exactly one reverse proxy (e.g. Render), set this to `1`; the app then trusts only the entry `X-Forwarded-For` chain has from *your* proxy specifically (counted from the right), never anything earlier in the chain that the original client could have forged.
- **The server must run with `--no-proxy-headers`.** uvicorn has its own independent proxy-trust layer (`--proxy-headers`, enabled by default, trusting connections from `127.0.0.1`) that rewrites the request's client IP *before* this app's own code ever runs. Left enabled, it silently overrides our own `TRUSTED_PROXY_HOPS` logic — worse, during local testing (client connects from `127.0.0.1`, which uvicorn trusts by default) it means a spoofed `X-Forwarded-For` header can bypass rate limiting entirely, even with `TRUSTED_PROXY_HOPS=0`. Disabling it makes this app's own logic the single source of truth.

## Setup

1. **Create a virtual environment and install dependencies:**

   ```bash
   python -m venv venv
   venv\Scripts\activate       # Windows
   pip install -r requirements.txt
   ```

2. **Configure environment variables.** Copy `.env.example` to `.env`:

   ```
   DATABASE_URL=postgresql+psycopg://user:password@host/dbname?sslmode=require
   BASE_URL=http://127.0.0.1:8000
   RATE_LIMIT_STORAGE_URI=rediss://default:<password>@<your-instance>.upstash.io:6379
   CORS_ORIGINS=http://localhost:3000,http://localhost:5173
   TRUSTED_PROXY_HOPS=0
   ```

   `DATABASE_URL` must use the `postgresql+psycopg://` scheme (psycopg 3), not the bare `postgresql://` Neon gives by default. `BASE_URL` should match wherever this API is actually reachable — it's used to build the `short_url` returned by `/shorten`. `RATE_LIMIT_STORAGE_URI` needs Upstash's **Redis protocol** connection string (`rediss://...`, TLS), not its separate REST API URL/token — find it on the database's page under "Connect" → pick a Redis client (not "REST"). Set `TRUSTED_PROXY_HOPS=1` only once actually deployed behind a real reverse proxy (see Design notes above).

3. **Run database migrations:**

   ```bash
   alembic upgrade head
   ```

4. **Start the dev server:**

   ```bash
   uvicorn app.main:app --reload --port 8000 --no-proxy-headers
   ```

## Running tests

```bash
pip install -r requirements-dev.txt
pytest -v
```

Tests run against the real Neon connection configured in `.env`, each wrapped in a transaction that's always rolled back — no separate test database needed, and nothing persists.

### Troubleshooting: DB connection hangs

If `alembic upgrade head` or the app hangs (not errors — just never returns) while connecting to Neon, it may be an IPv6 routing issue on your network: Neon's pooler hostname resolves to both IPv6 and IPv4 addresses, IPv6 is tried first, and if your network can't actually route IPv6 to AWS, the connection stalls on an unreachable address instead of falling back quickly. Fix: add `hostaddr=<an IPv4 address for your endpoint>` and `connect_timeout=10` as query params on `DATABASE_URL`, forcing a direct IPv4 connection while keeping the hostname (needed for Neon's TLS/SNI-based routing). Find a working IPv4 address with `nslookup <your-pooler-hostname>`.

## Roadmap (Phase 2)

- Self-contained auth (register/login/JWT, scoped to this project — no dependency on other services) so links can have an owner
- `owner_id` on `URL`, plus list/delete endpoints scoped to the authenticated user
- Anonymous creation stays supported; authenticated users just get management capabilities anonymous users don't
