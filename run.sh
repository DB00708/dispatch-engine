#!/usr/bin/env bash
# Dispatch Engine: one command to start, check or stop the app. Needs only Docker.
#
#   ./run.sh              start the app and open it in the browser
#   ./run.sh check        run every check: lint, types, unit, e2e, logs
#   ./run.sh stop         stop everything
#   ./run.sh logs         follow the container logs
#
# Add --db to start or check with Postgres + Redis.
# On Windows (PowerShell or cmd) use run.cmd instead.
set -uo pipefail
cd "$(dirname "$0")"

command="start"
db=()
for arg in "$@"; do
  case "$arg" in
    start | check | stop | logs) command=$arg ;;
    --db) db=(--env-file .env.db) ;;
    -h | --help | help) command=help ;;
    *)
      echo "Unknown option: $arg (see ./run.sh help)" >&2
      exit 2
      ;;
  esac
done

green=$'\033[32m'
red=$'\033[31m'
bold=$'\033[1m'
reset=$'\033[0m'

fail() {
  printf '\n%s%s%s\n' "$red" "$1" "$reset" >&2
  exit 1
}

compose() {
  docker compose ${db[@]+"${db[@]}"} "$@"
}

preflight() {
  command -v docker >/dev/null 2>&1 ||
    fail "Docker is not installed. Install Docker Desktop (Windows/macOS) or Docker Engine (Linux): https://docs.docker.com/get-docker/"
  docker compose version >/dev/null 2>&1 ||
    fail "Docker Compose v2 is missing. Update Docker Desktop, or install the docker-compose-plugin package."
  docker info >/dev/null 2>&1 ||
    fail "Docker is installed but not running. Start Docker Desktop and wait until it says the engine is running (on Linux: start the docker service, or check you may use it without sudo), then run this again."
}

# Port of the app if it is already running, else nothing.
running_port() {
  docker compose port web 80 2>/dev/null | head -n 1 | sed 's/.*://'
}

port_busy() {
  (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null
}

# Keep the current port if the app is up; else WEB_PORT; else the first free one from 8080.
choose_port() {
  local current
  current=$(running_port)
  if [ -n "$current" ]; then
    echo "$current"
  elif [ -n "${WEB_PORT:-}" ]; then
    echo "$WEB_PORT"
  else
    local port
    for port in $(seq 8080 8099); do
      if ! port_busy "$port"; then
        echo "$port"
        return 0
      fi
    done
    fail "Ports 8080-8099 are all in use. Pick one with: WEB_PORT=9090 ./run.sh"
  fi
}

open_browser() {
  [ -n "${CI:-}${NO_BROWSER:-}" ] && return 0
  if command -v open >/dev/null 2>&1; then
    open "$1"
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$1" >/dev/null 2>&1 &
  elif command -v cmd.exe >/dev/null 2>&1; then
    cmd.exe /c start "" "$1" >/dev/null 2>&1
  fi
  return 0
}

start() {
  preflight
  WEB_PORT=$(choose_port) || exit 1
  export WEB_PORT
  echo "Building and starting the app (the first run downloads images and takes a few minutes)..."
  compose up --build -d --wait || fail "The app did not start. See what happened with: ./run.sh logs"
  local url="http://localhost:$WEB_PORT"
  printf '\n%s%sDispatch Engine is running%s\n' "$bold" "$green" "$reset"
  printf '  App:       %s\n  API docs:  %s/docs\n  Stop:      ./run.sh stop\n' "$url" "$url"
  open_browser "$url"
}

check() {
  preflight
  local args=()
  [ ${#db[@]} -gt 0 ] && args+=(--db)
  # Leave the app running afterwards if it was running before.
  [ -n "$(running_port)" ] && args+=(--keep)
  WEB_PORT=$(choose_port) || exit 1
  export WEB_PORT
  bash scripts/check-all.sh ${args[@]+"${args[@]}"}
}

stop() {
  preflight
  docker compose --profile db --profile tools down --remove-orphans &&
    printf '%sStopped.%s\n' "$green" "$reset"
}

case "$command" in
  start) start ;;
  check) check ;;
  stop) stop ;;
  logs)
    preflight
    compose logs -f --tail 100
    ;;
  help) sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//' ;;
esac
