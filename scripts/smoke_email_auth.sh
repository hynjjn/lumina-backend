#!/usr/bin/env bash
# Smoke test email/password auth: signup, login, conflicts, guest upgrade + merge.
set -euo pipefail

BASE="${BASE:-http://localhost:8765}"
say() { printf '\n\033[1m== %s ==\033[0m\n' "$*"; }
tok() { uv run python -c "import sys,json;print(json.load(sys.stdin)['access_token'])"; }
uid() { uv run python -c "import sys,json;print(json.load(sys.stdin)['user']['id'])"; }
guest_flag() { uv run python -c "import sys,json;print(json.load(sys.stdin)['user']['is_guest'])"; }

# ── 1. Plain signup (no guest) ──────────────────────────────────────────────
say "POST /auth/signup alice@x.com → 201, is_guest=false"
RES=$(curl -fsS -X POST -H "Content-Type: application/json" \
  -d '{"email":"alice@x.com","password":"correct horse","name":"Alice"}' "$BASE/auth/signup")
TOK_ALICE=$(echo "$RES" | tok); UID_ALICE=$(echo "$RES" | uid)
echo "  uid=$UID_ALICE is_guest=$(echo "$RES" | guest_flag)"

say "POST /auth/signup alice@x.com again → 409"
echo "  status=$(curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' \
  -d '{"email":"alice@x.com","password":"another one"}' "$BASE/auth/signup")"

# ── 2. Login (happy + wrong password) ───────────────────────────────────────
say "POST /auth/login wrong password → 401"
echo "  status=$(curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' \
  -d '{"email":"alice@x.com","password":"wrong"}' "$BASE/auth/login")"

say "POST /auth/login correct → 200, same uid"
RES=$(curl -fsS -X POST -H "Content-Type: application/json" \
  -d '{"email":"alice@x.com","password":"correct horse"}' "$BASE/auth/login")
LOGIN_UID=$(echo "$RES" | uid)
echo "  uid=$LOGIN_UID (== $UID_ALICE? $([ "$LOGIN_UID" = "$UID_ALICE" ] && echo yes || echo NO))"

# ── 3. Guest upgrade via signup: guest's data must survive ──────────────────
say "create guest, give them an article, then signup → upgrade in place"
GUEST=$(curl -fsS -X POST "$BASE/auth/guest")
TOK_G=$(echo "$GUEST" | tok); UID_G=$(echo "$GUEST" | uid)
echo "  guest uid=$UID_G"
curl -fsS -X POST -H "Authorization: Bearer $TOK_G" -H "Content-Type: application/json" \
  -d '{"title":"From guest","content":"saved before signup"}' "$BASE/articles" > /dev/null

RES=$(curl -fsS -X POST -H "Authorization: Bearer $TOK_G" -H "Content-Type: application/json" \
  -d '{"email":"bob@x.com","password":"sup3r secret"}' "$BASE/auth/signup")
TOK_B=$(echo "$RES" | tok); UID_B=$(echo "$RES" | uid)
echo "  signup uid=$UID_B (== guest uid? $([ "$UID_B" = "$UID_G" ] && echo yes ✓ || echo NO))"
echo "  is_guest after upgrade=$(echo "$RES" | guest_flag)"

ARTICLES=$(curl -fsS -H "Authorization: Bearer $TOK_B" "$BASE/articles" | uv run python -c "import sys,json;d=json.load(sys.stdin);print(len(d),d[0]['title'] if d else '')")
echo "  bob's article count: $ARTICLES (expect: 1 From guest)"

# ── 4. Guest merge via login: different guest joins an existing account ─────
say "new guest creates 2 articles, then logs in as alice → merge"
GUEST2=$(curl -fsS -X POST "$BASE/auth/guest")
TOK_G2=$(echo "$GUEST2" | tok); UID_G2=$(echo "$GUEST2" | uid)
curl -fsS -X POST -H "Authorization: Bearer $TOK_G2" -H "Content-Type: application/json" \
  -d '{"title":"guest art 1","content":"a"}' "$BASE/articles" > /dev/null
curl -fsS -X POST -H "Authorization: Bearer $TOK_G2" -H "Content-Type: application/json" \
  -d '{"title":"guest art 2","content":"b"}' "$BASE/articles" > /dev/null
echo "  guest uid=$UID_G2 had 2 articles before login"

RES=$(curl -fsS -X POST -H "Authorization: Bearer $TOK_G2" -H "Content-Type: application/json" \
  -d '{"email":"alice@x.com","password":"correct horse"}' "$BASE/auth/login")
LOGIN_UID=$(echo "$RES" | uid)
TOK_ALICE2=$(echo "$RES" | tok)
echo "  login uid=$LOGIN_UID (== alice's original uid? $([ "$LOGIN_UID" = "$UID_ALICE" ] && echo yes ✓ || echo NO))"

ALICE_COUNT=$(curl -fsS -H "Authorization: Bearer $TOK_ALICE2" "$BASE/articles" | uv run python -c "import sys,json;print(len(json.load(sys.stdin)))")
echo "  alice's articles after merge: $ALICE_COUNT (expect 2 — guest's data moved to alice)"

GUEST_CHECK=$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $TOK_G2" "$BASE/auth/me")
echo "  /me with old guest token: status=$GUEST_CHECK (expect 401, guest row deleted)"

# ── 5. Email validation ─────────────────────────────────────────────────────
say "POST /auth/signup bad email → 422"
echo "  status=$(curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' \
  -d '{"email":"not-an-email","password":"goodpassword"}' "$BASE/auth/signup")"

say "POST /auth/signup short password → 422"
echo "  status=$(curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' \
  -d '{"email":"new@x.com","password":"short"}' "$BASE/auth/signup")"

echo
echo "all checks ran."
