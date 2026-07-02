#!/usr/bin/env bash
# Superpowers Integration — Progress Tracker
# 用法: bash ~/.hermes/scripts/track-superpowers.sh
# 每次改動後可以 run 嚟 verify 同記錄

set -euo pipefail

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
AGENT_DIR="$HERMES_HOME/hermes-agent"
BACKUP_DIR="$HERMES_HOME/backups"
CHANGELOG="$HERMES_HOME/changelogs/superpowers-integration.md"
SKILLS_DIR="$HERMES_HOME/skills"
NOW=$(date '+%Y-%m-%d %H:%M:%S')

echo "=========================================="
echo " Superpowers Integration — Status Report"
echo " $NOW"
echo "=========================================="
echo ""

# 1. Check 1% Rule + Red Flags in system prompt
echo "--- System Prompt (prompt_builder.py) ---"
if grep -q "SUPERPOWERS-1%-RULE" "$AGENT_DIR/agent/prompt_builder.py"; then
    echo "  ✅ 1% Rule injected"
else
    echo "  ❌ 1% Rule NOT found"
fi
if grep -q "RED-FLAGS" "$AGENT_DIR/agent/prompt_builder.py"; then
    echo "  ✅ Red Flags section present"
else
    echo "  ❌ Red Flags NOT found"
fi

# 2. Check skill_utils.py new functions
echo ""
echo "--- skill_utils.py ---"
for fn in extract_skill_triggers extract_skill_red_flags extract_skill_iron_laws; do
    if grep -q "def $fn" "$AGENT_DIR/agent/skill_utils.py"; then
        echo "  ✅ $fn() present"
    else
        echo "  ❌ $fn() NOT found"
    fi
done

# 3. Check context_compressor.py
echo ""
echo "--- context_compressor.py ---"
if grep -q "1% chance" "$AGENT_DIR/agent/context_compressor.py"; then
    echo "  ✅ Compaction reminder present"
else
    echo "  ❌ Compaction reminder NOT found"
fi

# 4. Check skills with Red Flags
echo ""
echo "--- Skills with Red Flags ---"
count=0
for skill_yaml in $(find "$SKILLS_DIR" -name "SKILL.md"); do
    if grep -q "red_flags:" "$skill_yaml"; then
        name=$(head -5 "$skill_yaml" | grep "^name:" | cut -d: -f2 | tr -d ' ')
        echo "  ✅ $name"
        count=$((count + 1))
    fi
done
echo "  Total: $count skills with Red Flags"

# 5. Check skills with Iron Laws
echo ""
echo "--- Skills with Iron Laws ---"
count2=0
for skill_yaml in $(find "$SKILLS_DIR" -name "SKILL.md"); do
    if grep -q "iron_laws:" "$skill_yaml"; then
        name=$(head -5 "$skill_yaml" | grep "^name:" | cut -d: -f2 | tr -d ' ')
        echo "  ✅ $name"
        count2=$((count2 + 1))
    fi
done
echo "  Total: $count2 skills with Iron Laws"

# 6. Check skills with triggers
echo ""
echo "--- Skills with Triggers ---"
count3=0
for skill_yaml in $(find "$SKILLS_DIR" -name "SKILL.md"); do
    if grep -q "triggers:" "$skill_yaml"; then
        name=$(head -5 "$skill_yaml" | grep "^name:" | cut -d: -f2 | tr -d ' ')
        echo "  ✅ $name"
        count3=$((count3 + 1))
    fi
done
echo "  Total: $count3 skills with Triggers"

# 7. Backup verification
echo ""
echo "--- Backup ---"
latest_backup=$(ls -td "$BACKUP_DIR"/superpowers-integration-* 2>/dev/null | head -1)
if [ -n "$latest_backup" ]; then
    echo "  ✅ Latest backup: $(basename $latest_backup)"
    ls -1 "$latest_backup"
else
    echo "  ❌ No backup found"
fi

echo ""
echo "=========================================="
echo " Report saved to changelog"
echo "=========================================="
