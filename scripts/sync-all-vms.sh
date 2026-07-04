#!/bin/bash
# sync-all-vms.sh — Unified VM sync across Oracle, Zeabur, ZO
# Uses GitHub (hermes-backup) as single source of truth
# Usage: sync-all-vms.sh [push|pull|status]

set -euo pipefail

MODE="${1:-status}"
REPO_DIR="$HOME/hermes-backup"
INVENTORY="$REPO_DIR/inventory.yml"
SSH_KEY="$HOME/.ssh/zeabur_key"

color_ok()  { echo -e "\033[0;32m$1\033[0m"; }
color_warn(){ echo -e "\033[1;33m$1\033[0m"; }
color_err() { echo -e "\033[0;31m$1\033[0m"; }

# Parse inventory YAML (fallback if yq not installed)
get_vm_field() {
    local vm="$1"
    local field="$2"
    if command -v yq >/dev/null 2>&1; then
        yq -r ".vms.${vm}.${field}" "$INVENTORY"
    else
        awk -v vm="$vm" -v field="$field" '
            /^  [a-z0-9-]+:/{
                gsub(/[ :]/, "", $1)
                current = $1
            }
            current == vm && $0 ~ "^    " field ":" {
                sub(/^    [^:]+: */, "")
                print
                exit
            }
        ' "$INVENTORY" | tr -d '"'
    fi
}

# Run SSH command on remote VM
run_ssh() {
    local user="$1"
    local host="$2"
    local port="${3:-22}"
    local password="${4:-}"
    local cmd="$5"

    if [ -n "$password" ]; then
        sshpass -p "$password" ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -p "$port" "$user@$host" "$cmd" 2>/dev/null
    else
        ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -p "$port" -i "$SSH_KEY" "$user@$host" "$cmd" 2>/dev/null
    fi
}

# Get remote git HEAD
remote_head() {
    local vm="$1"
    local user=$(get_vm_field "$vm" ssh_user)
    local host=$(get_vm_field "$vm" ssh_host)
    local port=$(get_vm_field "$vm" ssh_port)
    local password=$(get_vm_field "$vm" ssh_password)
    local scripts_dir=$(get_vm_field "$vm" scripts_dir)
    [ "$password" == "true" ] && password="@Q2%YTCbe%)mvSGQ42" || password=""
    run_ssh "$user" "$host" "$port" "$password" "cd $scripts_dir && git rev-parse HEAD 2>/dev/null" || echo "UNREACHABLE"
}

# Pull remote changes to GitHub, then pull locally (from local perspective)
pull_vm() {
    local vm="$1"
    echo "Pulling from $vm..."
    local user=$(get_vm_field "$vm" ssh_user)
    local host=$(get_vm_field "$vm" ssh_host)
    local port=$(get_vm_field "$vm" ssh_port)
    local password=$(get_vm_field "$vm" ssh_password)
    local scripts_dir=$(get_vm_field "$vm" scripts_dir)
    [ "$password" == "true" ] && password="@Q2%YTCbe%)mvSGQ42" || password=""

    run_ssh "$user" "$host" "$port" "$password" "cd $scripts_dir && git add -A && git commit -m 'auto: sync from $vm' >/dev/null 2>&1; git push origin main >/dev/null 2>&1 || true"
    cd "$REPO_DIR" && git pull origin main
    color_ok "✓ Pulled from $vm"
}

# Push local changes to GitHub, then pull on remote VM
push_vm() {
    local vm="$1"
    echo "Pushing to $vm..."
    local user=$(get_vm_field "$vm" ssh_user)
    local host=$(get_vm_field "$vm" ssh_host)
    local port=$(get_vm_field "$vm" ssh_port)
    local password=$(get_vm_field "$vm" ssh_password)
    local scripts_dir=$(get_vm_field "$vm" scripts_dir)
    [ "$password" == "true" ] && password="@Q2%YTCbe%)mvSGQ42" || password=""

    cd "$REPO_DIR" && git push origin main
    run_ssh "$user" "$host" "$port" "$password" "cd $scripts_dir && git pull origin main"
    color_ok "✓ Pushed to $vm"
}

# Show sync status for all VMs
show_status() {
    echo "=== VM Sync Status (GitHub as source of truth) ==="
    cd "$REPO_DIR"
    local local_hash=$(git rev-parse HEAD | cut -c1-8)
    echo "Local ($HOSTNAME): $local_hash"

    for vm in $(grep -E "^  [a-z0-9-]+:" "$INVENTORY" | sed -E 's/^  ([a-z0-9-]+):.*/\1/'); do
        local remote=$(remote_head "$vm" | cut -c1-8)
        if [ "$remote" == "UNREACHABLE" ]; then
            color_err "  $vm: UNREACHABLE"
        elif [ "$remote" == "$local_hash" ]; then
            color_ok "  $vm: $remote ✓ synced"
        else
            color_warn "  $vm: $remote ⚠ behind/ahead"
        fi
    done
}

# Main
case "$MODE" in
    status)
        show_status
        ;;
    pull)
        if [ -z "${2:-}" ]; then
            echo "Usage: sync-all-vms.sh pull <vm-name>"
            exit 1
        fi
        pull_vm "$2"
        ;;
    push)
        if [ -z "${2:-}" ]; then
            echo "Usage: sync-all-vms.sh push <vm-name>"
            exit 1
        fi
        push_vm "$2"
        ;;
    sync-all)
        echo "Pushing local to GitHub, then pulling all VMs..."
        cd "$REPO_DIR" && git push origin main
        for vm in $(grep -E "^  [a-z0-9-]+:" "$INVENTORY" | sed -E 's/^  ([a-z0-9-]+):.*/\1/'); do
            push_vm "$vm"
        done
        ;;
    *)
        echo "Usage: sync-all-vms.sh [status|pull <vm>|push <vm>|sync-all]"
        echo "  status    — show git sync status of all VMs"
        echo "  pull <vm> — pull changes from a VM to GitHub and then local"
        echo "  push <vm> — push local changes to GitHub and then a VM"
        echo "  sync-all  — push local to GitHub, then pull on every VM"
        ;;
esac
