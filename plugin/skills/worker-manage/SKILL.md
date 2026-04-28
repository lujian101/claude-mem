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

Claude Code's Bash tool runs commands with stdin **not** connected to a TTY. When worker-service.cjs detects non-TTY, it outputs `{"continue": true, "suppressOutput": true}` instead of human-readable text. This is normal hook protocol output — **ignore it**. Use exit code and HTTP health checks to determine success/failure.

## Plugin Root Resolution

All operations need to locate the plugin directory first. This uses the same 3-level fallback as the hooks in `hooks.json`:

1. `CLAUDE_PLUGIN_ROOT` environment variable (set by Claude Code)
2. Cache directory (versioned, managed by Claude Code)
3. Marketplace directory (final fallback)

```bash
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT}"
if [ -z "$PLUGIN_ROOT" ]; then
  PLUGIN_ROOT=$(\ls -dt $HOME/.claude/plugins/cache/thedotmack/claude-mem/[0-9]*/ 2>/dev/null | head -1)
  PLUGIN_ROOT="${PLUGIN_ROOT%/}"
fi
if [ -z "$PLUGIN_ROOT" ]; then
  PLUGIN_ROOT="$HOME/.claude/plugins/marketplaces/thedotmack/plugin"
fi
WORKER_SERVICE="$PLUGIN_ROOT/scripts/worker-service.cjs"
if [ ! -f "$WORKER_SERVICE" ]; then
  echo "ERROR: worker-service.cjs not found at $WORKER_SERVICE"
  echo "Is the claude-mem plugin installed?"
  exit 1
fi
```

Note: `\ls` avoids shell aliases that may add unwanted flags.

## Operations

Parse the operation from the user's message or skill args. Default to `status` if no operation specified.

### start

```bash
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT}"
if [ -z "$PLUGIN_ROOT" ]; then
  PLUGIN_ROOT=$(\ls -dt $HOME/.claude/plugins/cache/thedotmack/claude-mem/[0-9]*/ 2>/dev/null | head -1)
  PLUGIN_ROOT="${PLUGIN_ROOT%/}"
fi
if [ -z "$PLUGIN_ROOT" ]; then
  PLUGIN_ROOT="$HOME/.claude/plugins/marketplaces/thedotmack/plugin"
fi
WORKER_SERVICE="$PLUGIN_ROOT/scripts/worker-service.cjs"
if [ ! -f "$WORKER_SERVICE" ]; then
  echo "ERROR: worker-service.cjs not found."
  exit 1
fi
CLAUDE_MEM_MANUAL_START=true bun "$WORKER_SERVICE" start --force
```

**CLAUDE_MEM_MANUAL_START=true is required** — it bypasses the `WORKER_AUTO_START=false` guard which is designed to block hook-triggered auto-start, not manual CLI start. **--force** ensures the auto-start setting is also bypassed.

After running, verify with health check:

```bash
sleep 3 && curl -s http://localhost:37777/api/health
```

Report success or failure based on the health check response, not the CLI stdout.

### stop

```bash
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT}"
if [ -z "$PLUGIN_ROOT" ]; then
  PLUGIN_ROOT=$(\ls -dt $HOME/.claude/plugins/cache/thedotmack/claude-mem/[0-9]*/ 2>/dev/null | head -1)
  PLUGIN_ROOT="${PLUGIN_ROOT%/}"
fi
if [ -z "$PLUGIN_ROOT" ]; then
  PLUGIN_ROOT="$HOME/.claude/plugins/marketplaces/thedotmack/plugin"
fi
bun "$PLUGIN_ROOT/scripts/worker-service.cjs" stop
```

Verify the worker is down:

```bash
curl -s --max-time 3 http://localhost:37777/api/health 2>/dev/null && echo "WARNING: Worker still responding" || echo "Worker stopped successfully"
```

### restart

```bash
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT}"
if [ -z "$PLUGIN_ROOT" ]; then
  PLUGIN_ROOT=$(\ls -dt $HOME/.claude/plugins/cache/thedotmack/claude-mem/[0-9]*/ 2>/dev/null | head -1)
  PLUGIN_ROOT="${PLUGIN_ROOT%/}"
fi
if [ -z "$PLUGIN_ROOT" ]; then
  PLUGIN_ROOT="$HOME/.claude/plugins/marketplaces/thedotmack/plugin"
fi
CLAUDE_MEM_MANUAL_START=true bun "$PLUGIN_ROOT/scripts/worker-service.cjs" restart --force
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
  \ls -lt ~/.claude-mem/logs/*.log 2>/dev/null | head -5
fi
```

If the user wants more lines, use `tail -100` or `tail -200`. For older logs, specify the date.

## Error Handling

| Scenario | What to Tell User |
|----------|-------------------|
| worker-service.cjs not found | "claude-mem plugin is not installed. Install the plugin first." |
| bun not found (exit code 127) | "bun is required but not installed. Install from https://bun.sh" |
| Start fails — port in use | "Port 37777 is already in use. Check with: `netstat -ano \\| grep 37777`. A zombie process may be holding the port." |
| PID file exists but health check fails | "Worker appears to have crashed (PID file exists but not responding). Try `/worker-manage stop` then `/worker-manage start`." |
| Worker already running on start | "Worker is already running. Use `/worker-manage restart` to reload." |

## Windows Zombie Port Warning

**NEVER force-kill (taskkill /F, SIGKILL) the worker process on Windows.** This leaves the TCP socket in LISTENING state with no owning process — a "zombie port" that blocks new workers from starting until the OS reclaims it (can take minutes).

The stop command uses graceful HTTP shutdown (`POST /api/admin/shutdown`). If the worker doesn't respond within 15 seconds, the stop command logs a warning and cleans up the PID file but does NOT force-kill the process. If you encounter a zombie port:

1. Wait 2-5 minutes for Windows TCP stack to reclaim the socket
2. Then retry `/claude-mem:worker-manage start`
3. As a last resort, close all terminal windows that held connections to port 37777

## Notes

- The worker runs on port 37777 by default (configurable in `~/.claude-mem/settings.json`)
- Worker logs are at `~/.claude-mem/logs/worker-YYYY-MM-DD.log`
- PID file at `~/.claude-mem/worker.pid`
- On Windows, the worker is spawned via PowerShell as a detached process
- `WORKER_AUTO_START=false` in settings only blocks hook-triggered starts; manual starts via this skill work regardless
