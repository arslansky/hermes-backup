# 🔒 Tailscale Mesh + Network Hardening Runbook

> **分層導航**：bot/model/session 故障 → `OPENCLAW-OPS-RUNBOOK.md`｜新機裝設 → `HERMES-OPENCLAW-MULTI-VM-SETUP.md`｜整機重建 → `DISASTER-RECOVERY.md`｜**總索引 → `../README.md`**

Last-line maintenance record for the private Tailscale mesh and firewall lockdown
across the three-VM infrastructure. **Hermes (on Oracle) is the designated
last-line maintainer** — repair per this runbook before improvising.

> ⚠️ **No secrets in this file.** Gateway tokens, tskeys and key material live
> in their respective secret stores / vaults only.

---

## 1. Overview

```
                 ┌─────────────────────────────────────┐
                 │  Tailnet: tail183380.ts.net         │
                 │  Login: Google (neville.cwk@) + 2FA │
                 └─────────────────────────────────────┘
        WireGuard E2E encrypted, private, 2-3ms direct

  oracle-01 ─────────────── vm-17-222-ubuntu ────────────── (iPhone)
  100.96.203.104            100.121.1.3                   100.78.207.55
  Oracle VM (Hermes)        Zeabur VM (OpenClaw gateway)  Safari + app
  kernel mode               kernel mode                   (paired device)

  modal (ZO-01) 100.65.1.35 — userspace mode, outbound-only via SOCKS5
```

**Why it exists:**
- Private Hermes ↔ OpenClaw channel (no public internet hop)
- SSH (22) and OpenClaw dashboard (18789) closed to the public on all nodes
- Phone dashboard access over WireGuard (encrypted even in plain HTTP)

---

## 2. Node Reference

| Node | Tailnet IP | Mode | OS | Firewall | Role |
|---|---|---|---|---|---|
| oracle-01 | 100.96.203.104 | kernel TUN | Oracle Linux 9.8 (aarch64) | firewalld | Hermes host |
| vm-17-222-ubuntu | 100.121.1.3 | kernel TUN | Ubuntu (Zeabur) | ufw | OpenClaw gateway :18789 |
| modal | 100.65.1.35 | **userspace** | Debian 12 (gvisor container) | none | utility VM |
| iPhone | 100.78.207.55 | — | iOS | — | admin device |

Tailnet DNS: MagicDNS ON. `vm-17-222-ubuntu.tail183380.ts.net` resolves from
all kernel-mode nodes.

---

## 3. Per-Node Setup

### 3.1 Kernel-mode nodes (Oracle, Zeabur)

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo systemctl enable --now tailscaled          # Zeabur/Oracle have systemd
sudo tailscale up --hostname=<name>             # prints login.tailscale.com/a/xxx
# user approves the URL (Google session) — node appears in tailscale status
```

### 3.2 Zeabur: serve (HTTPS ingress to gateway)

```bash
sudo tailscale serve --bg 18789                  # 443 — BLOCKED by Zeabur platform
sudo tailscale serve --bg --https=8443 18789     # 8443 — works, real LE cert
sudo tailscale serve status
```

- Cert: Let's Encrypt for `vm-17-222-ubuntu.tail183380.ts.net` (auto, 90d)
- **Zeabur's platform intercepts ALL port 443** on the VM (presents a
  "Zeabur Pte. Ltd." cert). Never expect ts.net:443 to work.
- Dashboard URLs that work:
  - `http://100.121.1.3:18789` (tailnet HTTP)
  - `https://vm-17-222-ubuntu.tail183380.ts.net:8443` (tailnet HTTPS)

### 3.3 ZO-01: userspace mode (container has no CAP_NET_ADMIN)

```bash
nohup tailscaled --tun=userspace-networking \
     --socks5-server=localhost:1055 \
     > /var/log/tailscaled.log 2>&1 &
tailscale up --hostname=modal        # already authed; state file persists
```

- **`--socks5-server` is MANDATORY** — without it no proxy listens and no
  app can use the tailnet (node looks fine in `tailscale status`).
- Usage: `curl --proxy socks5://127.0.0.1:1055 http://100.121.1.3:18789/health`
- **No inbound**: other nodes cannot initiate connections to ZO.
- **ZO platform agent pitfall**: the zocomputer agent restarts tailscaled
  WITHOUT the socks5 flag after container reboot → proxy silently gone.
  Check `ss -tln | grep 1055` after any ZO restart; if missing, kill and
  relaunch with the full command above (auth persists in state file).
- ⚠️ Never `pkill -f "tailscale up"` over SSH — the pattern matches your own
  remote shell command line and kills the session. Use `pkill -x tailscaled`.

---

## 4. Firewall Posture (as of 2026-09-13)

### 4.1 Zeabur (ufw — was INACTIVE before this work)

```
Status: active (default deny incoming / allow outgoing)
22/tcp    ALLOW  100.64.0.0/10     ← SSH tailnet-only
18789/tcp ALLOW  100.64.0.0/10     ← OpenClaw dashboard tailnet-only
41641/udp ALLOW  Anywhere          ← tailscale direct
```

Rollback: `sudo ufw allow 22/tcp` / `sudo ufw allow 18789/tcp`

**⚠️ Stray-rule lesson:** a raw `iptables -A INPUT -p tcp --dport 18789 -j
ACCEPT` (bypassing ufw entirely) existed before this work — always check
`sudo iptables -L INPUT -n --line-numbers` for wildcard ACCEPTs above the
ufw chains, and `iptables-save | grep 18789`.

### 4.2 Oracle (firewalld)

- `public` zone (enp0s6): `ssh` service REMOVED
- Rich rule: `rule family=ipv4 source address=100.64.0.0/10 port port=22
  protocol=tcp accept`
- `41641/udp` allowed. `drop` zone for abusive CIDRs untouched.

Rollback: `sudo firewall-cmd --permanent --zone=public --add-service=ssh &&
sudo firewall-cmd --reload`

### 4.3 Consequence

Any device (laptop, phone, new VM) needs Tailscale CONNECTED to reach
22/18789 on Oracle or Zeabur. `Connection refused` ≠ machine dead.

---

## 5. OpenClaw Gateway Requirements (2026.8.2)

For the Control UI / serve proxy paths to work, `~/.openclaw/openclaw.json`
needs (set via `openclaw config set` + gateway restart):

```json
"gateway": {
  "controlUi": {
    "allowedOrigins": [
      "http://localhost:18789",
      "http://127.0.0.1:18789",
      "http://100.121.1.3:18789",
      "https://vm-17-222-ubuntu.tail183380.ts.net:8443"
    ]
  },
  "trustedProxies": ["127.0.0.1/32"]
}
```

- `trustedProxies` MUST be `["127.0.0.1/32"]` exactly — tailscale serve
  dials from loopback. Adding the tailnet IP to the list BREAKS direct
  access (trusted-IP requests without attribution headers get 403).
- Symptom of wrong config: HTTP 403
  `{"error":"Proxy client attribution is required"}`.
- Gateway token auth + device pairing still apply ON TOP of tailnet.
- Pairing approvals: `openclaw devices list` / `openclaw devices approve <id>`.
  Safari and the official iOS app **share one device key** (webview wrapper) —
  approving one approves both.

---

## 6. SSH Wiring

**Oracle `~/.ssh/config`:**
```
Host zeabur → HostName 100.121.1.3, User ubuntu, IdentityFile ~/.ssh/id_ed25519
Host zo     → HostName ts8.zocomputer.io, Port 10661, User root, IdentityFile ~/.ssh/zeabur_key
```

**Zeabur `~/.ssh/config`:**
```
Host oracle → HostName 100.96.203.104, User opc, IdentityFile ~/.ssh/oracle_vm_new
```
(pubkey comment `openclaw-oracle-vm`; authorized on Oracle `opc` account.
Two stale entries `140.245.111.2` / public IP were re-pointed to the tailnet
IP on 2026-09-13.)

---

## 7. Verification Checklist

```bash
# From any kernel-mode node:
tailscale status                        # all 4 nodes listed
tailscale ping 100.121.1.3              # direct, ~2-3ms
curl -s http://100.121.1.3:18789/health # {"ok":true,"status":"live"}

# Public exposure must FAIL (test from a non-tailnet host):
curl -m 6 http://43.156.247.30:18789/    # timeout
nc -z -w3 161.118.247.199 22             # fail

# ZO proxy health:
ssh zo 'ss -tln | grep 1055 && curl -s --proxy socks5://127.0.0.1:1055 \
  http://100.121.1.3:18789/health'

# Zeabur full stack (from Oracle):
ssh zeabur 'systemctl --user is-active openclaw-gateway.service; \
  curl -s http://127.0.0.1:18789/health'
```

---

## 8. Incident Lessons (don't relearn these)

1. **Zeabur platform owns :443** on Zeabur VMs — use :8443 for serve HTTPS.
2. **St iptables ACCEPT rules bypass ufw** — inspect raw chains, not just `ufw status`.
3. **tailscaled userspace mode needs `--socks5-server`** explicitly.
4. **gateway.trustedProxies with the tailnet IP breaks direct access** —
   loopback /32 only.
5. **iOS app == Safari device key** for Control UI pairing.
6. **Auth keys pasted in chat = revoked immediately**; use interactive
   `login.tailscale.com/a/xxx` flows or short-lived keys.
7. **Bot renamed the iPhone device** to a token string via admin API —
   rename in admin console for tidiness; cosmetic only.
8. **Never `pkill -f "<pattern>"` where the pattern appears in your own
   remote command** — self-kill via command-line match.

---

*Created 2026-09-13. Maintainer: Hermes Agent (Oracle). Update this file
whenever mesh/firewall topology changes.*
