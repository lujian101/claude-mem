#!/usr/bin/env python3
"""
Interactive build-diff-sync workflow for claude-mem.

Usage: python _mods/build-sync.py
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
CHECK_SYNC = SCRIPT_DIR / "check-sync.py"

total_files = 0
synced_files = 0


def confirm(prompt: str) -> bool:
    while True:
        ans = input(f"  {prompt} (y/n): ").strip().lower()
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False


def run(cmd: str, cwd: Path, label: str) -> bool:
    print(f"\n  Running: {cmd}")
    print("  " + "-" * 60)
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    print("  " + "-" * 60)
    if result.returncode != 0:
        print(f"\n  [ERROR] {label} failed (exit code {result.returncode})")
        return False
    print(f"  {label} OK.")
    return True


def step_build():
    global total_files
    print("\n  [Step 1/3] Build")
    print("  Command: npm run build")
    if confirm("Proceed with build?"):
        if not run("npm run build", PROJECT_DIR, "Build"):
            sys.exit(1)
    else:
        print("  Skipped.")


def step_diff() -> int:
    global total_files
    print("\n  [Step 2/3] Check diff")
    print("  Command: python _mods/check-sync.py")
    if confirm("Proceed with diff check?"):
        result = subprocess.run(
            [sys.executable, str(CHECK_SYNC)],
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
        )
        # Print the output
        print(result.stdout)
        if result.stderr:
            print(result.stderr)

        # Parse total files from output like "Total: 73 | OK: 68 | Modified: 5"
        diff_count = 0
        for line in result.stdout.strip().splitlines():
            if "Total:" in line:
                for part in line.split("|"):
                    part = part.strip()
                    if part.startswith("Total:"):
                        try:
                            total_files = int(part.split(":")[1].strip())
                        except ValueError:
                            pass
                    if part.startswith("Modified:") or part.startswith("New:"):
                        try:
                            diff_count += int(part.split(":")[1].strip())
                        except ValueError:
                            pass
        return diff_count
    else:
        print("  Skipped.")
        return -1  # skipped, unknown state


def step_sync(needs_sync: bool):
    global synced_files
    if not needs_sync:
        print("\n  [Step 3/3] Sync")
        print("  No differences found, sync skipped.")
        return

    print("\n  [Step 3/3] Sync to cache + marketplace")
    print("  Command: python _mods/check-sync.py --sync")
    if confirm("Proceed with sync?"):
        result = subprocess.run(
            [sys.executable, str(CHECK_SYNC), "--sync"],
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
        )
        print(result.stdout)
        if result.stderr:
            print(result.stderr)

        # Parse synced count
        for line in result.stdout.strip().splitlines():
            if "Synced" in line and "files" in line:
                try:
                    synced_files = int(line.split("Synced")[1].split("files")[0].strip())
                except (ValueError, IndexError):
                    synced_files = 0

        if synced_files > 0:
            print("  Run /reload-plugins in Claude Code to apply.")
    else:
        print("  Skipped.")


def main():
    print()
    print("  ============================================")
    print("   claude-mem Build & Sync Workflow")
    print("  ============================================")
    print(f"  Project: {PROJECT_DIR}")
    print()

    step_build()
    diff_count = step_diff()
    step_sync(needs_sync=(diff_count > 0))

    # Summary
    print()
    print("  ============================================")
    print("  Summary")
    print("  --------------------------------------------")
    print(f"  Total files:  {total_files}")
    print(f"  Synced:       {synced_files}")
    print("  ============================================")
    print()


if __name__ == "__main__":
    main()
