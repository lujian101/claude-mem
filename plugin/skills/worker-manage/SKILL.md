---
name: worker-manage
description: Manage the claude-mem worker daemon (start, stop, restart, status, logs). Use when the worker needs manual management, troubleshooting, or the user says "start worker", "stop worker", "worker status", "restart worker", "check worker", "worker logs".
---

# Worker Manage

Manage the claude-mem worker daemon directly from Claude Code. No need to switch terminals.

## When to Use

Trigger when users mention worker management:

- "Start the worker" / "启动 worker"
- "Stop the worker" / "停止 worker"
- "Restart the worker" / "重启 worker"
- "Worker status" / "Worker 状态" / "check worker"
- "Worker logs" / "查看 worker 日志"
- Any mention of worker not responding, worker issues, or port 37777

## Important: Non-TTY Output

Claude Code's Bash tool runs commands with stdin **not** connected to a TTY. When worker-cli.js detects non-TTY, it outputs `{"continue": true, "suppressOutput": true}` instead of human-readable text. This is normal hook protocol output — **ignore it**. Use exit code and HTTP health checks to determine success/failure.

## CLI Auto-Detection

All operations need to find worker-cli.js first. Use this bash pattern:

```bash
WORKER_CLI=$(\ls -d ~/.claude/plugins/cache/thedotmack/claude-mem/*/scripts/worker-cli.js 2>/dev/null | sort -r | head -1)
if [ -z "$WORKER_CLI" ]; then
  echo "ERROR: worker-cli.js not found in plugin cache."
  echo "Is the claude-mem plugin installed? Run /install in Claude Code first."
  exit 1
fi
```

If this fails, report to user: "claude-mem plugin is not installed or not cached yet."

## Operations

Parse the operation from the user's message or skill args. Default to `status` if no operation specified.

### start

```bash
WORKER_CLI=$(\ls -d ~/.claude/plugins/cache/thedotmack/claude-mem/*/scripts/worker-cli.js 2>/dev/null | sort -r | head -1)
if [ -z "$WORKER_CLI" ]; then echo "ERROR: worker-cli.js not found. Is the plugin installed?"; exit 1; fi
CLAUDE_MEM_MANUAL_START=true bun "$WORKER_CLI" start
```

**CLAUDE_MEM_MANUAL_START=true is required** — it bypasses the `WORKER_AUTO_START=false` guard which is designed to block hook-triggered auto-start, not manual CLI start.

After running, verify with health check:

```bash
sleep 3 && curl -s http://localhost:37777/api/health
```

Report success or failure based on the health check response, not the CLI stdout.

### stop

```bash
WORKER_CLI=$(\ls -d ~/.claude/plugins/cache/thedotmack/claude-mem/*/scripts/worker-cli.js 2>/dev/null | sort -r | head -1)
if [ -z "$WORKER_CLI" ]; then echo "ERROR: worker-cli.js not found."; exit 1; fi
bun "$WORKER_CLI" stop
```

Verify the worker is down:

```bash
curl -s http://localhost:37777/api/health 2>/dev/null && echo "WARNING: Worker still responding" || echo "Worker stopped successfully"
```

### restart

```bash
WORKER_CLI=$(\ls -d ~/.claude/plugins/cache/thedotmack/claude-mem/*/scripts/worker-cli.js 2>/dev/null | sort -r | head -1)
if [ -z "$WORKER_CLI" ]; then echo "ERROR: worker-cli.js not found."; exit 1; fi
CLAUDE_MEM_MANUAL_START=true bun "$WORKER_CLI" restart
```

Verify with health check after a few seconds:

```bash
sleep 5 && curl -s http://localhost:37777/api/health
```

### status

Prefer HTTP health check over CLI status command (more reliable):

```bash
HEALTH=$(curl -s --max-time 3 http://localhost:37777/api/health 2>/dev/null)
if [ -n "$HEALTH" ]; then
  echo "Worker is RUNNING"
  echo "Health: $HEALTH"
  READINESS=$(curl -s --max-time 3 http://localhost:37777/api/readiness 2>/dev/null)
  echo "Readiness: $READINESS"
  if [ -f ~/.claude-mem/worker.pid ]; then
    echo "PID info: $(cat ~/.claude-mem/worker.pid)"
  fi
else
  echo "Worker is NOT responding on port 37777."
  if [ -f ~/.claude-mem/worker.pid ]; then
    echo "PID file exists but health check failed — worker may have crashed."
    echo "PID info: $(cat ~/.claude-mem/worker.pid)"
  else
    echo "No PID file found."
  fi
fi
```

Report the status clearly to the user.

### logs

Show today's worker log (last 50 lines):

```bash
LOG_FILE=~/.claude-mem/logs/worker-$(date +%Y-%m-%d).log
if [ -f "$LOG_FILE" ]; then
  tail -50 "$LOG_FILE"
else
  echo "No log file found for today."
  echo "Available logs:"
  ls -lt ~/.claude-mem/logs/*.log 2>/dev/null | head -5
fi
```

If the user wants more lines, use `tail -100` or `tail -200`. For older logs, specify the date.

## Error Handling

| Scenario | What to Tell User |
|----------|-------------------|
| worker-cli.js not found | "claude-mem plugin is not installed or not cached. Install the plugin first." |
| bun not found (exit code 127) | "bun is required but not installed. Install from https://bun.sh" |
| Start fails — port in use | "Port 37777 is already in use. Check with: `netstat -ano \\| grep 37777`. A zombie process may be holding the port." |
| PID file exists but health check fails | "Worker appears to have crashed (PID file exists but not responding). Try `/worker-manage stop` then `/worker-manage start`." |
| Worker already running on start | "Worker is already running. Use `/worker-manage restart` to reload." |

## Notes

- The worker runs on port 37777 by default (configurable in `~/.claude-mem/settings.json`)
- Worker logs are at `~/.claude-mem/logs/worker-YYYY-MM-DD.log`
- PID file at `~/.claude-mem/worker.pid`
- On Windows, the worker is spawned via PowerShell as a detached process
- `WORKER_AUTO_START=false` in settings only blocks hook-triggered starts; manual starts via this skill work regardless
