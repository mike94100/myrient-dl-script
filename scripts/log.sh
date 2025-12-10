#!/usr/bin/env bash
set -euo pipefail

# Config
LOG_DIR="${LOG_DIR:-./logs}"; mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_FILE:-$LOG_DIR/myrient-dl_$(date -u +'%Y%m%dT%H%M%SZ').log}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"  # INFO | WARN | ERROR

# Colors
RED='\e[0;31m'; YELLOW='\e[0;33m'; GREEN='\e[0;32m'; NC='\e[0m'

# Rotate last # logs
rotate_logs() { ls -1t "$LOG_DIR"/myrient-dl_*.log 2>/dev/null | tail -n +11 | xargs -r rm -f; }

# Filter log level
should_log() {
  case "$LOG_LEVEL" in
    ERROR) [[ "$1" == "ERROR" ]] ;;
    WARN)  [[ "$1" =~ ^(WARN|ERROR)$ ]] ;;
    INFO)  true ;;
    *)     true ;;
  esac
}

# Logger (colored to terminal, plain to file)
log() {
  local level="$1"; shift; should_log "$level" || return 0
  local message="$*"; local ts; ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  local color="$NC"
  if [[ "$level" == INFO ]]; then color="$GREEN"
  elif [[ "$level" == WARN ]]; then color="$YELLOW"
  elif [[ "$level" == ERROR ]]; then color="$RED"; fi
  printf "%b[%s] [%s] %s%b\n" "$color" "$ts" "$level" "$message" "$NC"
  printf "[%s] [%s] %s\n" "$ts" "$level" "$message" >> "$LOG_FILE"
}
info()  { log INFO  "$@"; }
warn()  { log WARN  "$@"; }
error() { log ERROR "$@"; }

# Log command output (stdout+stderr -> file & terminal)
run() { "$@" > >(tee -a "$LOG_FILE") 2> >(tee -a "$LOG_FILE" >&2); }

# Help function
usage() {
  echo "USAGE:"
  echo "rotate_logs"
  echo "  Rotate and keep only the last X log files"
  echo "info \"INFO\""
  echo -n "  "; info "Log an INFO message (green)"
  echo "warn  \"WARNING\""
  echo -n "  "; warn "Log a WARN message (yellow)"
  echo "error \"ERROR\""
  echo -n "  "; error "Log an ERROR message (red)"
  echo "run \"command\""
  echo "  Execute command and log its output"
  echo ""
  echo "Options:"
  echo "  -h, --help"
  echo "    Show this help message and demo"
  echo ""
}

# Parse command line arguments only if executed directly (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" && $# -gt 0 ]]; then
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
fi
