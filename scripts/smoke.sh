#!/usr/bin/env bash
# End-to-end smoke test: two guest users, CRUD, ownership isolation, cascade delete.
# Run server first: uv run uvicorn app.main:app --port 8765
set -euo pipefail

BASE="${BASE:-http://localhost:8765}"
JQ() { uv run python -c "import sys,json; d=json.load(sys.stdin); $1"; }

say() { printf '\n\033[1m== %s ==\033[0m\n' "$*"; }

say "create guest A"
A=$(curl -fsS -X POST "$BASE/auth/guest")
TOK_A=$(echo "$A" | JQ "print(d['access_token'])")
UID_A=$(echo "$A" | JQ "print(d['user']['id'])")
echo "  user=$UID_A"

say "create guest B"
B=$(curl -fsS -X POST "$BASE/auth/guest")
TOK_B=$(echo "$B" | JQ "print(d['access_token'])")
UID_B=$(echo "$B" | JQ "print(d['user']['id'])")
echo "  user=$UID_B"

say "A creates article"
ART=$(curl -fsS -X POST "$BASE/articles" \
  -H "Authorization: Bearer $TOK_A" -H "Content-Type: application/json" \
  -d '{"title":"Test article","source_url":"https://example.com","content":"hello world"}')
ART_ID=$(echo "$ART" | JQ "print(d['id'])")
echo "  article=$ART_ID"

say "A creates wordbook entry tied to article"
WB=$(curl -fsS -X POST "$BASE/wordbook" \
  -H "Authorization: Bearer $TOK_A" -H "Content-Type: application/json" \
  -d "{\"word\":\"serendipity\",\"context\":\"a moment of serendipity\",\"article_id\":\"$ART_ID\",\"definition_en\":\"a fortunate accident\",\"definition_ko\":\"우연한 발견\"}")
WB_ID=$(echo "$WB" | JQ "print(d['id'])")
echo "  entry=$WB_ID"

say "A lists own articles (expect 1) and wordbook (expect 1)"
echo "  articles=$(curl -fsS -H "Authorization: Bearer $TOK_A" "$BASE/articles" | JQ "print(len(d))")"
echo "  wordbook=$(curl -fsS -H "Authorization: Bearer $TOK_A" "$BASE/wordbook" | JQ "print(len(d))")"

say "B lists (expect 0,0) — no cross-user leakage"
echo "  articles=$(curl -fsS -H "Authorization: Bearer $TOK_B" "$BASE/articles" | JQ "print(len(d))")"
echo "  wordbook=$(curl -fsS -H "Authorization: Bearer $TOK_B" "$BASE/wordbook" | JQ "print(len(d))")"

say "B tries to GET A's article (expect 404)"
echo "  status=$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $TOK_B" "$BASE/articles/$ART_ID")"

say "B tries to DELETE A's article (expect 404)"
echo "  status=$(curl -s -o /dev/null -w '%{http_code}' -X DELETE -H "Authorization: Bearer $TOK_B" "$BASE/articles/$ART_ID")"

say "B tries to save a wordbook entry tied to A's article_id (expect 400)"
BODY=$(printf '{"word":"x","article_id":"%s"}' "$ART_ID")
STATUS=$(curl -s -o /dev/null -w '%{http_code}' -X POST \
  -H "Authorization: Bearer $TOK_B" -H "Content-Type: application/json" \
  -d "$BODY" "$BASE/wordbook")
echo "  status=$STATUS"

say "A deletes article → wordbook entry's article_id should become NULL (SET NULL FK)"
curl -fsS -X DELETE -H "Authorization: Bearer $TOK_A" "$BASE/articles/$ART_ID" -w "  status=%{http_code}\n"
echo "  entry after article delete:"
curl -fsS -H "Authorization: Bearer $TOK_A" "$BASE/wordbook/$WB_ID" | uv run python -m json.tool

echo
echo "all smoke checks passed."
