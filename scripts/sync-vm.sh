#!/bin/bash
# sync-vm.sh — VM 之間互相 sync
# Usage:
#   ./sync-vm.sh pull <vm-name>    從指定 VM 拉最新
#   ./sync-vm.sh push <vm-name>    推送去指定 VM
#   ./sync-vm.sh status            睇所有 VM 狀態
#   ./sync-vm.sh list             列出所有 VM

set -e

WORKSPACE="$HOME/.openclaw/workspace"
INVENTORY="$WORKSPACE/inventory.yml"
SSH_KEY_BASE="$HOME/.ssh"

# Color
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 讀 inventory
get_vm_ssh() {
    local vm="$1"
    grep -A10 "^  ${vm}:" "$INVENTORY" | grep "ssh_host:" | awk '{print $2}'
}

get_vm_user() {
    local vm="$1"
    grep -A10 "^  ${vm}:" "$INVENTORY" | grep "ssh_user:" | awk '{print $2}'
}

get_vm_roles() {
    local vm="$1"
    grep -A10 "^  ${vm}:" "$INVENTORY" | grep "roles:" | sed 's/.*roles: //' | tr -d '[]'
}

# SSH 到 VM 拉 backup
sync_pull() {
    local target="$1"
    local ssh_host=$(get_vm_ssh "$target")
    local ssh_user=$(get_vm_user "$target")
    
    if [ -z "$ssh_host" ]; then
        echo -e "${RED}ERROR:${NC} VM '$target' not found in inventory"
        echo "Run './sync-vm.sh list' to see available VMs"
        exit 1
    fi
    
    echo -e "${YELLOW}Pulling from${NC} $target ($ssh_user@$ssh_host)..."
    
    # SSH 去 target VM，踢佢 git push
    ssh -o StrictHostKeyChecking=no "$ssh_user@$ssh_host" << 'ENDSSH'
        cd ~/.openclaw/workspace
        git add -A
        git commit -m "Auto-sync: $(date +%Y%m%d_%H%M%S)" 2>/dev/null || echo "Nothing to commit"
        git push origin master 2>/dev/null || echo "Push failed or not needed"
ENDSSH
    
    echo -e "${GREEN}✓${NC} Pulled from $target"
    
    # 然後喺本地 pull
    echo -e "${YELLOW}Pulling to local...${NC}"
    cd "$WORKSPACE"
    git pull origin master
    echo -e "${GREEN}✓${NC} Local updated"
}

# SSH 去 VM push 過嚟
sync_push() {
    local target="$1"
    local ssh_host=$(get_vm_ssh "$target")
    local ssh_user=$(get_vm_user "$target")
    
    if [ -z "$ssh_host" ]; then
        echo -e "${RED}ERROR:${NC} VM '$target' not found in inventory"
        exit 1
    fi
    
    echo -e "${YELLOW}Pushing to${NC} $target ($ssh_user@$ssh_host)..."
    
    # 先 push 本地
    cd "$WORKSPACE"
    git push origin master
    
    # 然後 SSH 去 target VM pull
    ssh -o StrictHostKeyChecking=no "$ssh_user@$ssh_host" << 'ENDSSH'
        cd ~/.openclaw/workspace
        git pull origin master
        echo "Remote updated"
ENDSSH
    
    echo -e "${GREEN}✓${NC} Pushed to $target"
}

# 列出所有 VM
sync_list() {
    if [ ! -f "$INVENTORY" ]; then
        echo -e "${RED}ERROR:${NC} inventory.yml not found"
        echo "Create it at: $INVENTORY"
        exit 1
    fi
    
    echo "=== Available VMs ==="
    grep "^  [a-z0-9-]*:" "$INVENTORY" | while read -r line; do
        vm=$(echo "$line" | sed 's/:.*//' | xargs)
        roles=$(get_vm_roles "$vm")
        ssh_host=$(get_vm_ssh "$vm")
        printf "  ${GREEN}%-15s${NC}  %-20s  %s\n" "$vm" "$roles" "$ssh_host"
    done
}

# 睇 VM 狀態
sync_status() {
    if [ ! -f "$INVENTORY" ]; then
        echo -e "${RED}ERROR:${NC} inventory.yml not found"
        exit 1
    fi
    
    echo "=== VM Sync Status ==="
    
    # 本地
    cd "$WORKSPACE"
    local_hash=$(git rev-parse HEAD 2>/dev/null | cut -c1-8)
    echo -e "  ${GREEN}local${NC}   $local_hash $(git log -1 --format='%s' 2>/dev/null)"
    
    # 每個 VM
    grep "^  [a-z0-9-]*:" "$INVENTORY" | while read -r line; do
        vm=$(echo "$line" | sed 's/:.*//' | xargs)
        ssh_host=$(get_vm_ssh "$vm")
        ssh_user=$(get_vm_user "$vm")
        
        if [ -n "$ssh_host" ]; then
            remote_hash=$(ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no "$ssh_user@$ssh_host" "cd ~/.openclaw/workspace && git rev-parse HEAD 2>/dev/null" 2>/dev/null | cut -c1-8)
            if [ -n "$remote_hash" ]; then
                if [ "$remote_hash" = "$local_hash" ]; then
                    echo -e "  ${GREEN}$vm${NC}   $remote_hash ✓ (synced)"
                else
                    echo -e "  ${YELLOW}$vm${NC}   $remote_hash ⚠ (behind local)"
                fi
            else
                echo -e "  ${RED}$vm${NC}   unreachable"
            fi
        fi
    done
}

# Main
case "$1" in
    pull)
        if [ -z "$2" ]; then
            echo "Usage: ./sync-vm.sh pull <vm-name>"
            ./sync-vm.sh list
            exit 1
        fi
        sync_pull "$2"
        ;;
    push)
        if [ -z "$2" ]; then
            echo "Usage: ./sync-vm.sh push <vm-name>"
            ./sync-vm.sh list
            exit 1
        fi
        sync_push "$2"
        ;;
    status)
        sync_status
        ;;
    list)
        sync_list
        ;;
    *)
        echo "Usage:"
        echo "  ./sync-vm.sh pull <vm>   # Pull from VM"
        echo "  ./sync-vm.sh push <vm>   # Push to VM"
        echo "  ./sync-vm.sh status      # Show sync status"
        echo "  ./sync-vm.sh list        # List all VMs"
        ;;
esac
