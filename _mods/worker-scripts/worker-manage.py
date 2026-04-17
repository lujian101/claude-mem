#!/usr/bin/env python3
"""
claude-mem worker management utility.

Usage:
  python worker-manage.py start
  python worker-manage.py stop
  python worker-manage.py status
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

CACHE_ROOT = Path.home() / ".claude" / "plugins" / "cache" / "thedotmack" / "claude-mem"


def find_cli() -> Optional[Path]:
    """Auto-detect worker-cli.js by scanning installed versions."""
    if not CACHE_ROOT.is_dir():
        return None
    versions = sorted(
        [d for d in CACHE_ROOT.iterdir() if d.is_dir()],
        key=lambda d: d.name,
        reverse=True,
    )
    for v in versions:
        cli = v / "scripts" / "worker-cli.js"
        if cli.is_file():
            return cli
    return None


def run_cli(action: str):
    cli = find_cli()
    if cli is None:
        print(f"[ERROR] worker-cli.js not found in {CACHE_ROOT}")
        print("Is the plugin installed? Run /plugin in Claude Code first.")
        input("Press Enter to exit...")
        sys.exit(1)

    print(f"Version: {cli.parent.parent.name}")
    print(f"CLI:     {cli}")
    print()
    env = os.environ.copy()
    if action == "start":
        env["CLAUDE_MEM_MANUAL_START"] = "true"
    subprocess.run(["bun", str(cli), action], env=env)
    input("Press Enter to exit...")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("start", "stop", "status"):
        print("Usage: python worker-manage.py [start|stop|status]")
        sys.exit(1)
    run_cli(sys.argv[1])
