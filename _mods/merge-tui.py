#!/usr/bin/env python3
"""
Interactive TUI wrapper for upstream-merge-guard.py.

Provides a menu-driven interface for the upstream merge safety workflow.
Run: python _mods/merge-tui.py
"""

import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
GUARD_SCRIPT = SCRIPT_DIR / "upstream-merge-guard.py"
PROJECT_DIR = SCRIPT_DIR.parent

BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
RESET = "\033[0m"


def clear():
    print("\033[2J\033[H", end="")


def run_guard(args: list[str]) -> int:
    """Run upstream-merge-guard.py with given args, return exit code."""
    result = subprocess.run(
        [sys.executable, str(GUARD_SCRIPT)] + args,
        cwd=str(PROJECT_DIR),
    )
    return result.returncode


def get_status() -> dict:
    """Gather current state info for the status line."""
    info = {"snapshot": False, "tag": "", "ahead": 0, "branch": ""}

    # Check snapshot manifest
    manifest = SCRIPT_DIR / ".merge-snapshot.json"
    if manifest.exists():
        import json
        with open(manifest) as f:
            data = json.load(f)
        info["snapshot"] = True
        info["tag"] = data.get("tag", "")

    # Upstream ahead count
    r = subprocess.run(
        ["git", "rev-list", "--count", "HEAD..upstream/main"],
        cwd=str(PROJECT_DIR),
        capture_output=True, text=True,
    )
    if r.returncode == 0 and r.stdout.strip():
        info["ahead"] = int(r.stdout.strip())

    # Current branch
    r = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=str(PROJECT_DIR),
        capture_output=True, text=True,
    )
    if r.returncode == 0:
        info["branch"] = r.stdout.strip()

    return info


def print_header(info: dict):
    clear()
    print(f"{BOLD}{'=' * 52}{RESET}")
    print(f"{BOLD}  Claude-Mem  Upstream Merge Guard{RESET}")
    print(f"{BOLD}{'=' * 52}{RESET}")
    print()

    # Status line
    parts = [f"Branch: {CYAN}{info['branch']}{RESET}"]

    if info["snapshot"]:
        parts.append(f"Snapshot: {GREEN}{info['tag']}{RESET}")
    else:
        parts.append(f"Snapshot: {DIM}none{RESET}")

    if info["ahead"] > 0:
        parts.append(f"Upstream: {YELLOW}{info['ahead']} commits ahead{RESET}")
    else:
        parts.append(f"Upstream: {GREEN}up to date{RESET}")

    for p in parts:
        print(f"  {p}")
    print()


def print_menu():
    menu = [
        ("1", "Snapshot", "Create tag + hash manifest before merge", GREEN),
        ("2", "Preview",  "Show upstream changes and conflict risk", CYAN),
        ("3", "Merge",    "Execute upstream/main merge", YELLOW),
        ("4", "Verify",   "Check all files against snapshot", GREEN),
        ("5", "Diff",     "Show detailed diff (snapshot vs now)", CYAN),
    ]

    print(f"  {BOLD}{'Key':<5} {'Command':<12} Description{RESET}")
    print(f"  {'-' * 46}")
    for key, name, desc, color in menu:
        print(f"  {BOLD}[{key}]{RESET}  {color}{name:<12}{RESET} {desc}")

    print()
    print(f"  {BOLD}[0]{RESET}  {'Exit':<12} Quit")
    print(f"  {'-' * 46}")


def prompt_choice() -> str:
    try:
        choice = input(f"\n  {BOLD}>{RESET} ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return "0"
    return choice


def pause():
    input(f"\n  {DIM}Press Enter to continue...{RESET}")


def main():
    if not GUARD_SCRIPT.exists():
        print(f"{RED}Error: {GUARD_SCRIPT.name} not found in {SCRIPT_DIR}{RESET}")
        sys.exit(1)

    while True:
        info = get_status()
        print_header(info)
        print_menu()
        choice = prompt_choice()

        if choice == "0":
            print(f"\n  Bye.")
            break
        elif choice == "1":
            clear()
            run_guard(["snapshot"])
            pause()
        elif choice == "2":
            clear()
            run_guard(["--no-fetch", "preview"])
            pause()
        elif choice == "3":
            clear()
            print(f"{YELLOW}  About to merge upstream/main. Make sure snapshot exists!{RESET}\n")
            rc = run_guard(["merge"])
            if rc != 0:
                pause()
        elif choice == "4":
            clear()
            run_guard(["verify"])
            pause()
        elif choice == "5":
            clear()
            run_guard(["diff"])
            pause()
        else:
            continue


if __name__ == "__main__":
    main()
