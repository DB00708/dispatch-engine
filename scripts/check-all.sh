#!/usr/bin/env bash
# Run every check in Docker and print a pass/fail summary. Needs only Docker.
# Usually called through ./run.sh check (or run.cmd check on Windows).
#
#   ./scripts/check-all.sh           in-memory storage, no cache
#   ./scripts/check-all.sh --db      the same against Postgres + Redis
#   ./scripts/check-all.sh --keep    leave the stack running afterwards
#
# The app is published on WEB_PORT (default 8080); the API is reached through it.
set -uo pipefail
cd "$(dirname "$0")/.."

if ! docker info >/dev/null 2>&1; then
  echo "Docker is not running (or not installed). Start Docker Desktop, then try again." >&2
  exit 1
fi

compose=(docker compose)
mode="in-memory storage, no cache"
storage="memory"
cache="none"
keep=false
for arg in "$@"; do
  case "$arg" in
    --db) compose+=(--env-file .env.db); mode="Postgres + Redis"; storage="postgres"; cache="redis" ;;
    --keep) keep=true ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

green=$'\033[32m'
red=$'\033[31m'
bold=$'\033[1m'
reset=$'\033[0m'
names=()
outcomes=()

step() {
  local name=$1
  shift
  printf '\n%s▶ %s%s\n' "$bold" "$name" "$reset"
  names+=("$name")
  if "$@"; then outcomes+=(pass); else outcomes+=(fail); fi
}

logs_clean() {
  local hits
  hits=$("${compose[@]}" logs --no-color 2>&1 \
    | grep -iE 'warn|error|exception|traceback|fatal|deprecat|" 5[0-9][0-9] ' \
    | grep -vE '" 4[0-9][0-9] ' || true)
  if [ -n "$hits" ]; then
    echo "$hits"
    return 1
  fi
  echo "No warnings or errors in any container log."
}

run_tool() {
  "${compose[@]}" run --rm -T "$@"
}

step "API: ruff, mypy (strict), pytest" run_tool --build api-tests
step "UI: npm ci (Node 22)" run_tool tools ci
step "UI: ESLint, TypeScript, Vitest, production build" run_tool tools run check
step "Stack: build and start ($mode)" "${compose[@]}" up --build -d --wait
step "API e2e: direct to the API" run_tool \
  -e E2E_EXPECT_STORAGE="$storage" -e E2E_EXPECT_CACHE="$cache" api-tests pytest -m e2e
step "API e2e: through nginx" run_tool -e E2E_BASE_URL=http://web api-tests pytest -m e2e
step "UI e2e: Playwright (Chromium)" run_tool e2e
step "Container logs: no warnings or errors" logs_clean

if [ "$keep" = false ]; then
  "${compose[@]}" down >/dev/null 2>&1
fi

failed=0
printf '\n%sSummary (%s)%s\n' "$bold" "$mode" "$reset"
for i in "${!names[@]}"; do
  if [ "${outcomes[$i]}" = pass ]; then
    printf '  %s✔ PASS%s  %s\n' "$green" "$reset" "${names[$i]}"
  else
    printf '  %s✘ FAIL%s  %s\n' "$red" "$reset" "${names[$i]}"
    failed=$((failed + 1))
  fi
done
if [ "$failed" -eq 0 ]; then
  printf '\n%s%sALL GREEN: %d/%d checks passed%s\n' "$bold" "$green" "${#names[@]}" "${#names[@]}" "$reset"
  [ "$keep" = true ] && echo "Stack still running: http://localhost:${WEB_PORT:-8080}"
  exit 0
fi
printf '\n%s%s%d of %d checks failed%s\n' "$bold" "$red" "$failed" "${#names[@]}" "$reset"
exit 1
