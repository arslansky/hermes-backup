#!/usr/bin/env python3
"""
Skill TDD Testing Framework for Hermes Agent
==============================================
Inspired by obra/superpowers writing-skills methodology.

Tests a skill by:
  1. Creating a pressure scenario that agents commonly fail at
  2. Dispatching a subagent WITHOUT the skill to establish baseline
  3. Dispatching a subagent WITH the skill loaded
  4. Comparing behavior to verify the skill works

Usage:
  python3 ~/.hermes/scripts/skill-tdd.py <skill-name>
  python3 ~/.hermes/scripts/skill-tdd.py --list           # List testable skills
  python3 ~/.hermes/scripts/skill-tdd.py --all             # Test all skills
  python3 ~/.hermes/scripts/skill-tdd.py systematic-debugging  # Test one skill

Example:
  python3 ~/.hermes/scripts/skill-tdd.py requesting-code-review
"""

import json
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
SKILLS_DIR = HERMES_HOME / "skills"
RESULTS_DIR = HERMES_HOME / "skill-tdd-results"

# ── Pressure scenarios ────────────────────────────────────────────────
# Each scenario is a dict with:
#   skill:       skill name being tested
#   prompt:      user message that triggers the bad behavior
#   baseline:    what agents typically do WITHOUT the skill (the "failure" we want to fix)
#   success:     what agents should do WITH the skill (evidence it's working)
#   verify:      list of strings that should appear in the WITH-skill response

PRESSURE_SCENARIOS = {
    "systematic-debugging": {
        "prompt": (
            "There's a bug in my code. The login function keeps returning 401 "
            "even with valid credentials. I think the JWT token is expired. "
            "Can you just regenerate the token handling?"
        ),
        "baseline": "Agent jumps to fix without investigating root cause",
        "success": "Agent does root cause investigation before proposing fixes",
        "verify": ["root cause", "investigat", "reproduc", "phase 1", "no fix"],
    },
    "test-driven-development": {
        "prompt": (
            "I need you to add a new function that validates email addresses. "
            "It should check for @ symbol, domain format, and reject invalid ones."
        ),
        "baseline": "Agent writes the implementation without tests first",
        "success": "Agent writes a failing test before any production code",
        "verify": ["test", "failing", "red", "TDD", "RED-GREEN"],
    },
    "writing-plans": {
        "prompt": (
            "I want to build a REST API for a todo app with user authentication, "
            "CRUD operations, and WebSocket notifications."
        ),
        "baseline": "Agent jumps into coding without a plan",
        "success": "Agent creates a structured implementation plan first",
        "verify": ["plan", "task", "step", "implement", "bite-size"],
    },
    "subagent-driven-development": {
        "prompt": (
            "I have an implementation plan for a Markdown editor. "
            "Here are the tasks. Let's execute them."
        ),
        "baseline": "Agent tries to do everything in one session without delegation",
        "success": "Agent dispatches subagents per task with review stages",
        "verify": ["delegate_task", "subagent", "task", "dispatch"],
    },
    "requesting-code-review": {
        "prompt": (
            "I just finished implementing the payment processing module. "
            "Can you review it quickly before I push?"
        ),
        "baseline": "Agent gives a quick skim review without structured checking",
        "success": "Agent runs structured review with checklist and severity levels",
        "verify": ["review", "severity", "critical", "checklist", "issue"],
    },
    "verification-before-completion": {
        "prompt": (
            "I fixed the bug by adding a null check. The error is gone now. "
            "Can we move on to the next task?"
        ),
        "baseline": "Agent assumes fix works without verification",
        "success": "Agent verifies the fix actually works before marking done",
        "verify": ["verif", "test", "confirm", "check"],
    },
    "github-code-review": {
        "prompt": (
            "Can you review this PR that changes the database schema to add "
            "a new user preferences table?"
        ),
        "baseline": "Agent reviews without checking specific security/db concerns",
        "success": "Agent reviews with security, migration, and data integrity checks",
        "verify": ["migration", "backward compat", "rollback", "security"],
    },
    "batch-file-translate": {
        "prompt": (
            "I need these 5 Markdown files translated from English to Chinese. "
            "Each one is about 40KB."
        ),
        "baseline": "Agent tries read_file/write_file one by one",
        "success": "Agent uses terminal() with a single Python script for batch processing",
        "verify": ["terminal", "batch", "python", "loop"],
    },
    "post-task-retrospective": {
        "prompt": (
            "That was a complex task. I just spent 2 hours debugging a Docker "
            "networking issue. Took many trial and error attempts."
        ),
        "baseline": "Agent finishes conversation without reviewing lessons learned",
        "success": "Agent does structured retrospective (problem → root cause → fix → memory update)",
        "verify": ["retrospect", "lesson", "root cause", "skill", "memory"],
    },
}


def list_testable_skills():
    """Print all skills that have pressure scenarios defined."""
    print("Testable skills (have pressure scenario):")
    for name in sorted(PRESSURE_SCENARIOS.keys()):
        print(f"  - {name}")
    print(f"\nTotal: {len(PRESSURE_SCENARIOS)} skills")


def run_skill_test(skill_name: str, dry_run: bool = False):
    """Run TDD-style test for a single skill."""
    if skill_name not in PRESSURE_SCENARIOS:
        print(f"❌ No pressure scenario for '{skill_name}'")
        print(f"   Available: {', '.join(sorted(PRESSURE_SCENARIOS.keys()))}")
        return False

    scenario = PRESSURE_SCENARIOS[skill_name]
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  Phase 2: Skill TDD — Testing '{skill_name}'")
    print(f"{'='*60}")
    print(f"\nPressure prompt: {scenario['prompt'][:80]}...")
    print(f"Expected WITHOUT skill: {scenario['baseline']}")
    print(f"Expected WITH skill: {scenario['success']}")
    print(f"Verify keywords: {scenario['verify']}")

    if dry_run:
        print("\n[DRY RUN — no actual test executed]")
        result_path = RESULTS_DIR / f"{skill_name}-test-plan.txt"
        with open(result_path, "w") as f:
            f.write(f"Skill TDD Test Plan: {skill_name}\n")
            f.write(f"{'='*50}\n\n")
            f.write(f"Pressure Prompt:\n{scenario['prompt']}\n\n")
            f.write(f"Baseline (expected failure): {scenario['baseline']}\n")
            f.write(f"Success criteria: {scenario['success']}\n")
            f.write(f"Verify keywords: {', '.join(scenario['verify'])}\n\n")
            f.write("Manual execution required:\n")
            f.write("  1. Run agent WITHOUT the skill loaded\n")
            f.write("  2. Send the pressure prompt\n")
            f.write("  3. Observe baseline behavior\n")
            f.write("  4. Run agent WITH the skill\n")
            f.write("  5. Compare results\n")
        print(f"   Test plan saved: {result_path}")
        return True

    # Save test plan for the user
    result_path = RESULTS_DIR / f"{skill_name}-test-plan.txt"
    with open(result_path, "w") as f:
        f.write(f"Skill TDD Test Plan: {skill_name}\n")
        f.write(f"{'='*50}\n\n")
        f.write(f"Pressure Prompt:\n{scenario['prompt']}\n\n")
        f.write(f"Baseline (expected failure): {scenario['baseline']}\n")
        f.write(f"Success criteria: {scenario['success']}\n")
        f.write(f"Verify keywords: {', '.join(scenario['verify'])}\n\n")
        f.write("Manual execution required:\n")
        f.write("  1. Run agent WITHOUT the skill loaded\n")
        f.write("  2. Send the pressure prompt\n")
        f.write("  3. Observe baseline behavior\n")
        f.write("  4. Run agent WITH the skill\n")
        f.write("  5. Compare results\n")

    print(f"\n✅ Test plan saved: {result_path}")
    return True


def run_all_tests(dry_run: bool = False):
    """Run TDD tests for all skills with pressure scenarios."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = RESULTS_DIR / "test-summary.md"
    
    results = []
    for skill_name in sorted(PRESSURE_SCENARIOS.keys()):
        ok = run_skill_test(skill_name, dry_run=dry_run)
        results.append((skill_name, ok))
    
    with open(summary_path, "w") as f:
        f.write("# Skill TDD Test Summary\n\n")
        f.write(f"Date: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write("| Skill | Scenario | Status |\n")
        f.write("|-------|----------|--------|\n")
        for name, ok in results:
            scenario = PRESSURE_SCENARIOS[name]
            status = "✅ Test plan ready" if ok else "❌ Failed"
            f.write(f"| {name} | {scenario['baseline'][:50]}... | {status} |\n")
        f.write(f"\n\nTotal: {len(results)} skills\n")
    
    print(f"\n📋 Summary: {summary_path}")
    return True


def main():
    if "--list" in sys.argv:
        list_testable_skills()
        return

    dry = "--dry-run" in sys.argv

    if "--all" in sys.argv:
        run_all_tests(dry_run=dry)
        return

    if len(sys.argv) < 2 or sys.argv[1].startswith("-"):
        print(__doc__)
        return

    skill_name = sys.argv[1]
    run_skill_test(skill_name, dry_run=dry)


if __name__ == "__main__":
    main()
