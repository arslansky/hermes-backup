# 🗂️ Scripts — Shared Directory

Both **Hermes Agent** and **OpenClaw** on this VM read from this directory via symlinks.  
Edit scripts here — both agents see the changes instantly.

## How it works

```
/home/opc/scripts/          ← 真實 files
├── mingpao_scraper.py      ←   Hermes cron uses (Mingpao daily digest)
├── run_mingpao_daily.sh    ←   Hermes cron wrapper
├── hermes_overview.py      ←   Hermes health overview
├── ...                     ←   All other scripts
│
~/.hermes/scripts/          ← symlinks → /home/opc/scripts/
~/.openclaw/workspace/ops/scripts/  ← symlinks → /home/opc/scripts/
```

| Agent | Path | Method |
|---|---|---|
| Hermes | `~/.hermes/scripts/` | Symlink |
| OpenClaw | `~/.openclaw/workspace/ops/scripts/` | Symlink |

## Script inventory

### Daily Ops

| Script | Purpose | Lang | Used by |
|---|---|---|---|
| `mingpao_scraper.py` | Mingpao news scraper (CloakBrowser + MiniMax AI) | Python | Hermes cron daily 06:15 |
| `run_mingpao_daily.sh` | Cron wrapper for Mingpao scraper | Bash | Hermes cron |
| `hermes_overview.py` | Hermes installation quick overview | Python | Hermes |
| `news_digest.py` | General news digest | Python | OpenClaw |
| `article_analyzer.py` | Article analysis utility | Python | OpenClaw |

### Zeabur Bots

| Script | Purpose | Lang |
|---|---|---|
| `tg_bot_zeabur01.py` | Zeabur01 Telegram bot | Python |
| `tg_bot_zeabur01_ttk.py` | Zeabur01 TG bot + TTK integration | Python |
| `tg_bot_zeabur01_with_db.py` | Zeabur01 TG bot with database | Python |

### Experiments & Tools

| Script | Purpose | Lang |
|---|---|---|
| `test_ttk.py` | TTK API endpoint test | Python |
| `fable_reasoner.py` | Fable reasoning system | Python |
| `hktmall_generator.py` | HKTMall content generator | Python |
| `minimax_demo.py` | MiniMax API demo | Python |
| `minimax_multidim_demo.py` | MiniMax multi-dimension demo | Python |
| `multillm_concept_demo.py` | Multi-LLM concept demo | Python |
| `reflection_demo.py` | Reflection pattern demo | Python |
| `analyze2.py` | Image/Markdown analyzer | Python |
| `analyze_image.py` | Single image analysis | Python |
| `analyze_images.py` | Batch image analysis | Python |

### JS Tools

| Script | Purpose |
|---|---|
| `news-to-pdf.js` | Convert news to PDF |
| `moomoo-scrape.js` | Moomoo financial scraper |
| `notegpt_extract.js` | NoteGPT extraction |
| `ytpdf.js` | YouTube transcript + PDF |

### Backup & Sync

| Script | Purpose |
|---|---|
| `backup.sh` | Workspace backup |
| `restore.sh` | Workspace restore |
| `bootstrap.sh` | Initial setup |
| `sync-vm.sh` | Multi-VM sync |
| `weekly-skills-backup.sh` | Weekly skills backup |

## Notes

- Symlinks created: 2026-07-04
- Original paths kept for backward compatibility
- Cron jobs reference `run_mingpao_daily.sh` by name — Hermes resolves via `~/.hermes/scripts/` which is symlinked
- Python scripts assume dependencies are installed under Python 3.11
- JS scripts require Node.js v22+ and relevant npm packages