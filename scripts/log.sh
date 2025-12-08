#!/usr/bin/env bash

LOG_FILE="./logs/myrient-dl.log"

log() {
    printf "[%s] %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | tee -a "$LOG_FILE"
}
