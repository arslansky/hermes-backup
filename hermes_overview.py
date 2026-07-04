#!/usr/bin/env python3
"""
Hermes Environment & State Overview
====================================
Run this to get a quick summary of the Hermes installation.
"""
import os, json, sqlite3
from datetime import datetime

HERMES = os.path.expanduser("~/.hermes")

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def fmt_size(n):
    for unit in ('B','K','M','G'):
        if abs(n) < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}T"

def dir_size(path):
    total = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            try:
                total += os.path.getsize(fp)
            except:
                pass
    return total

# ── Disk Usage ──
section("DISK USAGE")
paths = ["skills", "scripts", "cron", "logs", "memories", "cache", 
         "sessions", "gateway", "bin", "audio_cache", "image_cache", 
         "kanban", "sandboxes", "platforms"]
for p in paths:
    full = os.path.join(HERMES, p)
    if os.path.isdir(full):
        print(f"  {p:20s}  {fmt_size(dir_size(full)):>8s}")

# Config
for f in ["config.yaml", ".env", "SOUL.md", "state.db", "auth.json",
          "models_dev_cache.json", "gateway_state.json", "channel_directory.json"]:
    fp = os.path.join(HERMES, f)
    if os.path.isfile(fp):
        print(f"  {f:20s}  {fmt_size(os.path.getsize(fp)):>8s}")

total = dir_size(HERMES)
print(f"  {'─'*30}")
print(f"  {'TOTAL':20s}  {fmt_size(total):>8s}")

# ── Session Stats ──
section("SESSIONS")
db = os.path.join(HERMES, "state.db")
if os.path.exists(db):
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM sessions")
    cnt = cur.fetchone()[0]
    cur.execute("SELECT SUM(input_tokens), SUM(output_tokens), SUM(cache_read_tokens), SUM(cache_write_tokens), SUM(reasoning_tokens), SUM(api_call_count), SUM(message_count) FROM sessions")
    row = cur.fetchone()
    if row and row[0]:
        print(f"  Total sessions:       {cnt}")
        print(f"  Input tokens:         {row[0]:>12,}")
        print(f"  Output tokens:        {row[1]:>12,}")
        print(f"  Cache read tokens:    {row[2]:>12,}")
        print(f"  Reasoned tokens:      {row[4]:>12,}")
        print(f"  API calls:            {row[5]:>12,}")
        print(f"  Messages:             {row[6]:>12,}")
    cur.execute("SELECT id, model, started_at, message_count, input_tokens, output_tokens FROM sessions ORDER BY started_at DESC LIMIT 5")
    rows = cur.fetchall()
    if rows:
        print()
        print("  Recent sessions:")
        for r in rows:
            sid, model, ts, msgs, inp, out = r
            t = datetime.fromtimestamp(ts).strftime("%m/%d %H:%M") if ts else "?"
            print(f"    {t}  {model:25s}  msgs={msgs:>3}  in={inp:>8,}  out={out:>6,}")

# ── Cron Jobs ──
section("CRON JOBS")
cron_jobs = os.path.join(HERMES, "cron", "jobs.json")
if os.path.exists(cron_jobs):
    with open(cron_jobs) as f:
        jobs = json.load(f)
    if isinstance(jobs, dict):
        if "jobs" in jobs:
            jobs_list = jobs["jobs"]
        else:
            jobs_list = jobs.values()
    elif isinstance(jobs, list):
        jobs_list = jobs
    else:
        jobs_list = []
    
    for j in jobs_list:
        if isinstance(j, dict):
            name = j.get("name", j.get("id", "?"))
            sched = j.get("schedule", j.get("cron", "?"))
            script = j.get("script", "")
            print(f"  • {name}")
            print(f"    Schedule: {sched}")
            if script:
                print(f"    Script:   {script}")
            print()

# ── Skills ──
section("SKILLS")
skills_dir = os.path.join(HERMES, "skills")
found = False
for root, dirs, files in os.walk(skills_dir):
    if ".hub" in root or ".curator_state" in root:
        continue
    for f in files:
        if f == "SKILL.md":
            found = True
            rel = os.path.relpath(root, skills_dir)
            fp = os.path.join(root, f)
            with open(fp) as sf:
                desc = ""
                for line in sf:
                    if line.startswith("description:"):
                        desc = line.split(":",1)[1].strip()
                        break
                    if line.rstrip() == "---" and desc == "":
                        break
                print(f"  • {rel:30s}  {desc}")
if not found:
    print("  (no skills installed)")

# ── System ──
section("SYSTEM")
import subprocess
for cmd in [["uname","-r"], ["df","-h","/","--output=pcent"]]:
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
    out = " ".join(r.stdout.splitlines()[-1:]).strip()
    print(f"  {' '.join(cmd):20s}  {out}")

r = subprocess.run(["free","-h"], capture_output=True, text=True, timeout=5)
for line in r.stdout.splitlines():
    if "Mem:" in line:
        parts = line.split()
        print(f"  {'Memory':20s}  total={parts[1]}  used={parts[2]}  avail={parts[6]}")
        break

# ── OpenClaw Sessions ──
oc_sessions = os.path.expanduser("~/.openclaw/agents/main/sessions")
if os.path.isdir(oc_sessions):
    section("OPENCLAW SESSIONS")
    total_oc = 0
    for f in os.listdir(oc_sessions):
        if f.endswith(".jsonl"):
            fp = os.path.join(oc_sessions, f)
            sz = os.path.getsize(fp)
            total_oc += sz
            age = datetime.fromtimestamp(os.path.getmtime(fp)).strftime("%m/%d %H:%M")
            print(f"  {age}  {fmt_size(sz):>8s}  {f[:30]}")
    print(f"  {'─'*30}")
    print(f"  {'OC Total':20s}  {fmt_size(total_oc):>8s}")

print()
print("✅ Done")