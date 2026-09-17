# 🧠 Shared Skills & Knowledge

Shared workflows, skills, and knowledge files for all VMs.

## Structure

```
skills/
├── README.md                 ← 呢個檔案
└── （技能檔案放呢度）
```

## 重要指針

- **Multi-VM 架構文件**已搬去 `setup-guide/`（四份手冊，總索引喺 repo root `README.md`）
- 舊版 `multi-vm-setup.md`（2026-07）喺 `archive/multi-vm-setup-2026-07.md` 留底
- **VM 清單 / 故障排查 / 維修手冊一律睇 `../README.md` 嘅分層索引**，唔好喺呢度另起爐灶

## How it works

各 VM 共享：repo pull 落 `~/hermes-backup` 就用得：

```bash
cd ~/hermes-backup && git pull
```
