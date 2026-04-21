#!/usr/bin/env python3
"""
Check and sync claude-mem plugin files between working directory and installation paths.

Usage:
  python _mods/check-sync.py              # Check only, show differences
  python _mods/check-sync.py --diff       # Check, show all files
  python _mods/check-sync.py --sync       # Sync differences to cache & marketplace
  python _mods/check-sync.py --sync --diff  # Sync + show all files
"""

import hashlib
import json
import os
import shutil
import sys
import argparse
from datetime import datetime
from pathlib import Path

CACHE_ROOT = Path.home() / ".claude" / "plugins" / "cache" / "thedotmack" / "claude-mem"
MKT_ROOT = Path.home() / ".claude" / "plugins" / "marketplaces" / "thedotmack" / "plugin"

# Status markers
M_OK    = "."
M_DIFF  = "M"
M_NEW   = "+"


def md5(path: Path) -> str:
    if not path.is_file():
        return "-"
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:8]


def mtime_str(path: Path) -> str:
    if not path.is_file():
        return "                 "
    ts = datetime.fromtimestamp(path.stat().st_mtime)
    return ts.strftime("%m-%d %H:%M:%S")


def collect_files(root: Path) -> dict[str, Path]:
    if not root.is_dir():
        return {}
    result = {}
    for p in root.rglob("*"):
        if p.is_file():
            result[str(p.relative_to(root)).replace("\\", "/")] = p
    return result


def check_sync(work_dir: Path, show_diff: bool, do_sync: bool):
    # Detect version
    pkg = work_dir.parent / "package.json"
    version = "unknown"
    if pkg.is_file():
        with open(pkg) as f:
            version = json.load(f).get("version", "unknown")

    cache_dir = CACHE_ROOT / version
    mkt_dir = MKT_ROOT

    print(f" Version:  {version}")
    print(f" Source:   {work_dir}")
    print(f" Cache:    {cache_dir} {'[OK]' if cache_dir.is_dir() else '[MISSING]'}")
    print(f" Market:   {mkt_dir} {'[OK]' if mkt_dir.is_dir() else '[MISSING]'}")
    print()

    work_files = collect_files(work_dir)
    cache_files = collect_files(cache_dir)
    mkt_files = collect_files(mkt_dir)

    all_keys = sorted(set(work_files) | set(cache_files) | set(mkt_files))

    n_ok = n_diff = n_new = n_synced = 0
    lines = []

    for idx, key in enumerate(all_keys, 1):
        c_ok = key in cache_files
        m_ok = key in mkt_files
        w_ok = key in work_files

        c_hash = md5(cache_files[key]) if c_ok else "-"
        m_hash = md5(mkt_files[key]) if m_ok else "-"
        w_hash = md5(work_files[key]) if w_ok else "-"

        w_mtime = mtime_str(work_files[key]) if w_ok else ""

        if c_ok and m_ok and w_ok and c_hash == w_hash and m_hash == w_hash:
            marker = M_OK
            n_ok += 1
        elif not w_ok:
            marker = "?"
            # orphan files (not in work_dir) are not actionable, skip counting
        else:
            is_new = not c_ok or not m_ok
            if do_sync:
                if not c_ok or c_hash != w_hash:
                    dest = cache_dir / key
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(work_files[key], dest)
                if not m_ok or m_hash != w_hash:
                    dest = mkt_dir / key
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(work_files[key], dest)
                marker = M_NEW if is_new else M_DIFF
                n_synced += 1
            else:
                marker = M_NEW if is_new else M_DIFF
                if is_new:
                    n_new += 1
                else:
                    n_diff += 1

        show = (marker != M_OK and marker != "?") or show_diff
        if show:
            num = f"{idx:>3}"
            lines.append(f" {num} {w_mtime} {marker} {key}")

    # Print all collected lines
    for line in lines:
        print(line)

    # Summary
    print()
    parts = [f"Total: {len(all_keys)}"]
    parts.append(f"OK: {n_ok}")
    if do_sync:
        if n_synced > 0:
            parts.append(f"Synced: {n_synced}")
        else:
            parts.append("Already in sync")
    else:
        if n_diff:
            parts.append(f"Modified: {n_diff}")
        if n_new:
            parts.append(f"New: {n_new}")

    print(f" {' | '.join(parts)}")

    if do_sync and n_synced > 0:
        print(f"\n Synced {n_synced} files -> cache + marketplace")
        print(" Run /reload-plugins in Claude Code to apply.")

    if not show_diff and n_ok > 0:
        print(f" ({n_ok} identical files hidden, use --diff to show all)")

    return n_diff + n_new


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check and sync claude-mem plugin files")
    parser.add_argument("work_dir", nargs="?", default=None, help="Plugin working directory")
    parser.add_argument("--diff", action="store_true", help="Show all files including identical ones")
    parser.add_argument("--sync", action="store_true", help="Sync differences to cache & marketplace")
    args = parser.parse_args()

    if args.work_dir:
        work = Path(args.work_dir)
    else:
        script_dir = Path(__file__).resolve().parent
        work = script_dir.parent / "plugin"

    if not work.is_dir():
        print(f"Error: plugin directory not found at {work}")
        sys.exit(1)

    check_sync(work, args.diff, args.sync)
