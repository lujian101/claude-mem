#!/usr/bin/env python3
"""
Upstream merge safety guard for claude-mem fork.

Creates snapshots before merging upstream changes and verifies local
modifications survive the merge. Prevents silent loss of local patches.

Usage:
  python _mods/upstream-merge-guard.py snapshot   # Tag + hash all local changes
  python _mods/upstream-merge-guard.py preview    # Show upstream changes
  python _mods/upstream-merge-guard.py merge      # Execute upstream merge
  python _mods/upstream-merge-guard.py verify     # Check all files against snapshot
  python _mods/upstream-merge-guard.py diff       # Show full diff snapshot vs HEAD
"""

import hashlib
import json
import os
import subprocess
import sys
import argparse
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
MANIFEST_PATH = SCRIPT_DIR / ".merge-snapshot.json"
UPSTREAM_REF = "upstream/main"

# ANSI colors
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def cprint(color: str, msg: str):
    print(f"{color}{msg}{RESET}")


def run_git(args: list[str], cwd: Path = PROJECT_DIR, check: bool = True) -> tuple[int, str]:
    """Run a git command, return (returncode, stdout)."""
    result = subprocess.run(
        ["git"] + args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        print(f"{RED}git {' '.join(args)} failed:{RESET}")
        if result.stderr.strip():
            print(result.stderr.strip())
        sys.exit(1)
    return result.returncode, result.stdout.strip()


def file_hash(path: Path) -> str:
    """SHA-256 first 8 hex chars of file content."""
    if not path.is_file():
        return "-"
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:8]


def load_manifest() -> dict | None:
    """Load manifest if it exists, else None."""
    if MANIFEST_PATH.is_file():
        with open(MANIFEST_PATH) as f:
            return json.load(f)
    return None


def save_manifest(data: dict):
    with open(MANIFEST_PATH, "w") as f:
        json.dump(data, f, indent=2)


def get_modified_files() -> list[str]:
    """Get files that differ from HEAD (staged + unstaged)."""
    _, out = run_git(["diff", "--name-only", "HEAD"])
    if not out:
        return []
    return out.splitlines()


def get_head_file_hash(relpath: str) -> str:
    """Get hash of a file as it exists in HEAD commit."""
    _, out = run_git(["show", f"HEAD:{relpath}"], check=False)
    if not out:
        return "-"
    return hashlib.sha256(out.encode()).hexdigest()[:8]


# --- Commands ---

def cmd_snapshot(args):
    """Create a pre-merge snapshot: git tag + file hash manifest."""
    existing = load_manifest()
    if existing:
        cprint(YELLOW, f"Snapshot already exists from {existing['created']}")
        print(f"  Tag: {existing['tag']}")
        print(f"  Run 'verify' to check, or delete {MANIFEST_PATH.name} to re-snapshot.")
        return

    # Get modified files
    files = get_modified_files()
    if not files:
        cprint(GREEN, "No local modifications detected. Nothing to snapshot.")
        print("  (If you have committed local patches, this is expected.)")
        # Still create snapshot with empty files list for tag safety
        files = []

    # Build manifest
    tag_name = f"pre-merge-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    _, head_commit = run_git(["rev-parse", "--short", "HEAD"])
    _, upstream_commit = run_git(["rev-parse", "--short", UPSTREAM_REF], check=False)

    file_entries = {}
    for relpath in sorted(files):
        abs_path = PROJECT_DIR / relpath
        wt_hash = file_hash(abs_path)
        head_hash = get_head_file_hash(relpath)
        file_entries[relpath] = {
            "worktree_hash": wt_hash,
            "head_hash": head_hash,
            "dirty": wt_hash != head_hash,
        }

    manifest = {
        "tag": tag_name,
        "created": datetime.now().isoformat(timespec="seconds"),
        "head_commit": head_commit,
        "upstream_commit": upstream_commit or "unknown",
        "files": file_entries,
    }

    save_manifest(manifest)

    # Create git tag
    run_git(["tag", tag_name])

    cprint(GREEN, f"Snapshot created: {tag_name}")
    print(f"  HEAD:     {head_commit}")
    print(f"  Upstream: {upstream_commit or 'unknown'}")
    print(f"  Files:    {len(file_entries)} tracked")
    if file_entries:
        dirty_count = sum(1 for v in file_entries.values() if v["dirty"])
        if dirty_count:
            cprint(YELLOW, f"  ({dirty_count} files have uncommitted changes)")
    print(f"\n  Next: python _mods/upstream-merge-guard.py preview")


def cmd_preview(args):
    """Show upstream changes before merging."""
    if not args.no_fetch:
        print("Fetching upstream...")
        run_git(["fetch", "upstream"])

    # Check if upstream/main exists
    _, upstream_hash = run_git(["rev-parse", "--short", UPSTREAM_REF], check=False)
    if not upstream_hash:
        cprint(RED, f"Cannot resolve {UPSTREAM_REF}. Run 'git fetch upstream' first.")
        sys.exit(1)

    # Log
    _, log = run_git(["log", "HEAD..upstream/main", "--oneline"])
    if not log:
        cprint(GREEN, "Already up to date. No upstream changes to merge.")
        return

    commits = log.splitlines()
    cprint(BOLD, f"\nUpstream has {len(commits)} new commits:\n")
    for line in commits:
        print(f"  {line}")

    # Diff stat
    print()
    _, stat = run_git(["diff", "--stat", "HEAD..upstream/main"])
    if stat:
        print(stat)

    # Cross-reference: only warn about files that BOTH sides modified
    # (files that only exist in the fork are safe - git keeps them)
    manifest = load_manifest()
    if manifest and manifest["files"]:
        # Get merge base, then find what upstream actually changed
        _, merge_base = run_git(["merge-base", "HEAD", UPSTREAM_REF], check=False)
        if merge_base:
            _, upstream_changed = run_git(["diff", "--name-only", f"{merge_base}..{UPSTREAM_REF}"])
            _, our_changed = run_git(["diff", "--name-only", f"{merge_base}..HEAD"])
            upstream_set = set(upstream_changed.splitlines()) if upstream_changed else set()
            our_set = set(our_changed.splitlines()) if our_changed else set()
            overlap = our_set & upstream_set
            if overlap:
                cprint(YELLOW, f"\nWARNING: {len(overlap)} file(s) modified by BOTH sides (real conflict risk):")
                for f in sorted(overlap):
                    print(f"  {RED}*{RESET} {f}")
            else:
                cprint(GREEN, "\nNo overlapping changes detected. Merge should be clean.")

    print(f"\n  Next: python _mods/upstream-merge-guard.py merge")


def cmd_merge(args):
    """Execute upstream merge."""
    manifest = load_manifest()
    if not manifest:
        cprint(RED, "No snapshot found. Run 'snapshot' first.")
        sys.exit(1)

    print(f"Using snapshot: {manifest['tag']}")
    print(f"Merging {UPSTREAM_REF}...")

    rc, out = run_git(["merge", UPSTREAM_REF, "--no-edit"], check=False)

    if rc == 0:
        cprint(GREEN, "\nMerge successful!")
        print(f"  Next: python _mods/upstream-merge-guard.py verify")
    else:
        # Check for conflicts
        _, status = run_git(["status", "--porcelain"], check=False)
        conflicted = [line[3:] for line in status.splitlines() if line.startswith("UU") or line.startswith("AA")]
        if conflicted:
            cprint(RED, f"\nMerge conflicts in {len(conflicted)} file(s):")
            for f in conflicted:
                print(f"  {RED}CONFLICT{RESET} {f}")
            cprint(YELLOW, f"\nResolve conflicts, then run 'verify' to check your patches.")
            print(f"  Emergency rollback: git reset --hard {manifest['tag']}")
        else:
            print(out)


def cmd_verify(args):
    """Compare current state against snapshot."""
    manifest = load_manifest()
    if not manifest:
        cprint(RED, "No snapshot found. Run 'snapshot' first.")
        sys.exit(1)

    files = manifest["files"]
    if not files:
        cprint(GREEN, "No files were tracked in this snapshot.")
        return

    cprint(BOLD, f"Verifying snapshot: {manifest['tag']}")
    cprint(BOLD, f"{'STATUS':<10} {'FILE'}")
    print("-" * 60)

    n_ok = n_changed = n_lost = 0

    for relpath in sorted(files.keys()):
        entry = files[relpath]
        abs_path = PROJECT_DIR / relpath
        old_hash = entry["worktree_hash"]

        if not abs_path.exists():
            cprint(RED, f"{'LOST':<10} {relpath}")
            n_lost += 1
            continue

        current_hash = file_hash(abs_path)
        if current_hash == old_hash:
            cprint(GREEN, f"{'OK':<10} {relpath}")
            n_ok += 1
        else:
            status = "REVERTED" if current_hash == entry["head_hash"] else "CHANGED"
            cprint(RED, f"{status:<10} {relpath}")
            cprint(YELLOW, f"           was:{old_hash} now:{current_hash}")
            n_changed += 1

    print("-" * 60)
    parts = []
    if n_ok:
        parts.append(f"{GREEN}{n_ok} OK{RESET}")
    if n_changed:
        parts.append(f"{RED}{n_changed} CHANGED{RESET}")
    if n_lost:
        parts.append(f"{RED}{n_lost} LOST{RESET}")
    print(f"  {' | '.join(parts)}")

    if n_changed or n_lost:
        cprint(YELLOW, f"\nRun 'diff' to see what changed.")
        cprint(YELLOW, f"Rollback: git reset --hard {manifest['tag']}")
        sys.exit(1)
    else:
        cprint(GREEN, "\nAll local modifications intact!")


def cmd_diff(args):
    """Show full diff between snapshot tag and current state."""
    manifest = load_manifest()
    if not manifest:
        cprint(RED, "No snapshot found. Run 'snapshot' first.")
        sys.exit(1)

    tag = manifest["tag"]
    files = list(manifest["files"].keys())

    if not files:
        cprint(YELLOW, "No files tracked in this snapshot.")
        return

    # Filter: only source files, skip build artifacts
    SKIP_SUFFIXES = (".cjs", ".bundle.js", ".min.js")
    files = [f for f in files if not any(f.endswith(s) for s in SKIP_SUFFIXES)]

    # Filter to specific files if requested
    if args.files:
        files = [f for f in files if any(pat in f for pat in args.files)]

    if not files:
        cprint(YELLOW, "No source files to diff (all were build artifacts).")
        return

    print(f"Diff: {tag} -> HEAD ({len(files)} source files)\n")
    subprocess.run(
        ["git", "--no-pager", "diff", tag, "--"] + files,
        cwd=str(PROJECT_DIR),
    )


def main():
    parser = argparse.ArgumentParser(
        description="Upstream merge safety guard for claude-mem fork",
    )
    parser.add_argument("--no-fetch", action="store_true", help="Skip git fetch (use cached refs)")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("snapshot", help="Create pre-merge snapshot (tag + manifest)")
    sub.add_parser("preview", help="Show upstream changes before merging")
    sub.add_parser("merge", help="Execute upstream/main merge")
    sub.add_parser("verify", help="Verify current state against snapshot")

    diff_parser = sub.add_parser("diff", help="Show diff between snapshot and current HEAD")
    diff_parser.add_argument("files", nargs="*", help="Filter to files matching these patterns")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    dispatch = {
        "snapshot": cmd_snapshot,
        "preview": cmd_preview,
        "merge": cmd_merge,
        "verify": cmd_verify,
        "diff": cmd_diff,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
