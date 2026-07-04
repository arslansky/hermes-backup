#!/bin/bash
# health-check.sh — Health check across all VMs
# Reports: SSH reachability, disk space, load, service status, git sync status

set -euo pipefail

REPO_DIR="$HOME/hermes-backup"
INVENTORY="$REPO_DIR/inventory.yml"
REPORT_FILE="$HOME/.hermes/cron/output/health-check-latest.txt"

echo "=== Multi-VM Health Check ==="
echo "Started: $(date -Iseconds)"

# Ensure output dir exists
mkdir -p "$(dirname "$REPORT_FILE")"

# Helper: run a command over SSH on a target
run_ssh() {
    local user="$1"
    local host="$2"
    local port="${3:-22}"
    local password="${4:-}"
    local cmd="$5"

    if [ -n "$password" ]; then
        sshpass -p "$password" ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -p "$port" "$user@$host" "$cmd" 2>/dev/null || echo "SSH_FAIL"
    else
        ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -p "$port" -i "$HOME/.ssh/zeabur_key" "$user@$host" "$cmd" 2>/dev/null || echo "SSH_FAIL"
    fi
}

# Parse inventory using yq if available, else use simple grep fallback
get_vm_field() {
    local vm="$1"
    local field="$2"
    if command -v yq >/dev/null 2>&1; then
        yq -r ".vms.${vm}.${field}" "$INVENTORY"
    else
        grep -A20 "^  ${vm}:" "$INVENTORY" | grep "${field}:" | head -1 | sed -E "s/.*${field}: *//" | tr -d '"'
    fi
}

# Local health check
check_local() {
    echo ""
    echo "--- $(hostname -s) (local) ---"
    echo "Disk:"
    df -h / | tail -1 | awk '{print "  Used: "$3" / "$2" ("$5")"}'
    echo "Load: $(cat /proc/loadavg | awk '{print $1, $2, $3}')"
    echo "Services:"
    for svc in hermes-gateway openclaw-gateway; do
        status=$(systemctl --user is-active "$svc.service" 2>/dev/null || echo "unknown")
        echo "  $svc.service: $status"
    done
    echo "Git:"
    cd "$REPO_DIR"
    echo "  branch: $(git branch --show-current 2>/dev/null || echo unknown)"
    echo "  last commit: $(git log -1 --format='%h %s' 2>/dev/null || echo unknown)"
}

# Remote health check
check_remote() {
    local vm="$1"
    local ssh_host=$(get_vm_field "$vm" "ssh_host")
    local ssh_user=$(get_vm_field "$vm" "ssh_user")
    local ssh_port=$(get_vm_field "$vm" "ssh_port")
    local ssh_password=$(get_vm_field "$vm" "ssh_password")
    local scripts_dir=$(get_vm_field "$vm" "scripts_dir")

    echo ""
    echo "--- $vm ($ssh_user@$ssh_host:$ssh_port) ---"

    if [ "$ssh_password" == "true" ]; then
        # Zeabur uses password
        pass="@Q2%YTCbe%)mvSGQ42"
    else
        pass=""
    fi

    # SSH reachability
    result=$(run_ssh "$ssh_user" "$ssh_host" "$ssh_port" "$pass" "hostname" || echo "SSH_FAIL")
    if [ "$result" == "SSH_FAIL" ] || [ -z "$result" ]; then
        echo "  Status: UNREACHABLE"
        return
    fi
    echo "  Hostname: $result"

    # Disk
    run_ssh "$ssh_user" "$ssh_host" "$ssh_port" "$pass" "df -h / | tail -1 | awk '{print \"Used:\" \$3 \" / \" \$2 \" (\" \$5 \")\"}'"

    # Load
    run_ssh "$ssh_user" "$ssh_host" "$ssh_port" "$pass" "cat /proc/loadavg | awk '{print \"Load:\" \$1, \$2, \$3}'"

    # Services
    run_ssh "$ssh_user" "$ssh_host" "$ssh_port" "$pass" "for svc in hermes-gateway openclaw-gateway; do echo \"\$svc.service: \$(systemctl --user is-active \$svc.service 2>/dev/null || echo unknown)\"; done"

    # Git status in repo
    run_ssh "$ssh_user" "$ssh_host" "$ssh_port" "$pass" "cd $scripts_dir && git log -1 --format='%h %s' 2>/dev/null || echo git_not_found"
}

# Save report to file and stdout
exec > >(tee -a "$REPORT_FILE")

check_local

if [ -f "$INVENTORY" ]; then
    for vm in $(grep -E "^  [a-z0-9-]+:" "$INVENTORY" | sed -E 's/^  ([a-z0-9-]+):.*/\1/'); do
        check_remote "$vm"
    done
else
    echo ""
    echo "WARNING: inventory.yml not found at $INVENTORY"
fi

echo ""
echo "=== Health Check Complete ==="
echo "Report saved: $REPORT_FILE"
