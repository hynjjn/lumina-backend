# Lumina Backend

FastAPI backend for [Lumina](./lumina.md). Python 3.14, async SQLAlchemy, guest + Google OAuth.

## Setup

```bash
uv sync
cp .env.example .env   # then fill in JWT_SECRET, Google OAuth, Gemini key
uv run uvicorn app.main:app --reload
```

OpenAPI docs at <http://localhost:8000/docs>.

## Auth model

Every request needs a `Bearer <jwt>`. Tokens are valid for 30 days; guest rows inactive for 30 days are GC'd by `app.cleanup.purge_expired_guests` (run from cron). Three ways to obtain a token:

- **Guest** — `POST /auth/guest` mints a JWT bound to a new `User(is_guest=true)`. Frontend stashes it in `localStorage`. No login screen.
- **Email/password** — `POST /auth/signup` and `POST /auth/login`. Passwords hashed with `bcrypt`.
- **Google** — `GET /auth/google/login` → authorize URL → callback issues a JWT.

**Guest upgrade is uniform across all three.** If the caller sends an existing guest's bearer alongside signup/login/Google flow, two things can happen:
1. **Upgrade in place** (no matching account exists yet) — the guest row stays, but `is_guest=false` and email/password_hash/google_sub get attached. `user_id` is stable, no FK migration needed.
2. **Merge** (an account already exists for that email/google_sub) — the guest's `articles` and `wordbook_entries` are `UPDATE`'d to point at the existing user, then the guest row is deleted.

## Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `POST` | `/auth/guest` | — | Mint anonymous JWT + user row |
| `POST` | `/auth/signup` | guest token (optional) | Email/password signup. Upgrades guest row in place if guest bearer is sent. 409 on duplicate email |
| `POST` | `/auth/login` | guest token (optional) | Email/password login. Merges guest's data into the matched user if guest bearer is sent |
| `GET` | `/auth/google/login` | guest token (optional) | Returns Google authorize URL; if guest bearer present, embeds `guest_id` in signed `state` for upgrade |
| `GET` | `/auth/google/callback` | — | Exchanges code, upgrades-in-place or merges into existing user, returns new JWT |
| `GET` | `/auth/me` | bearer | Current user |
| `POST` `GET` `GET /{id}` `DELETE /{id}` | `/articles` | bearer | Reading list CRUD |
| `POST` | `/articles/import` | bearer | Fetch URL → trafilatura extract → save to reading list (rejects private IPs / non-http schemes) |
| `POST` `GET` `GET /{id}` `DELETE /{id}` | `/wordbook` | bearer | Wordbook CRUD |
| `POST` | `/rewrite` | bearer | Echo stub — Gemini wiring TODO |

End-to-end smoke: `scripts/smoke.sh` (server must be running on port 8765).

## Layout

```
app/
  main.py          # FastAPI app + lifespan create_all
  config.py        # pydantic-settings (.env)
  db.py            # async engine + Base + get_session (+ SQLite FK pragma)
  models.py        # User, Article, WordbookEntry
  schemas.py       # request/response models
  jwt_utils.py     # JWT + signed OAuth state
  passwords.py     # bcrypt hash / verify
  google_oauth.py  # Google authorize URL + code exchange
  deps.py          # current_user dependency
  extract.py       # SSRF-guarded URL fetch + trafilatura extract
  cleanup.py       # purge_expired_guests (ON DELETE CASCADE handles owned rows)
  routers/
    auth.py        # /auth/* (incl. guest-merge re-parenting of articles + wordbook)
    articles.py    # /articles CRUD
    wordbook.py    # /wordbook CRUD
    rewrite.py     # /rewrite stub
```
