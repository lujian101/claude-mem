# Worker 进程管理机制分析

引用计数 + 延迟回收

---

## 现状：PID 文件 + 孤儿清理（没有引用计数）

当前架构的核心问题是：**Worker 进程没有引用计数，最后一个 session 结束后 worker 依然存活**。只能靠重启电脑或 30 分钟孤儿清理来兜底。

---

## 核心文件清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `src/services/worker-spawner.ts` | 207 | Worker 启动入口，hook 调用的第一站 |
| `src/services/infrastructure/ProcessManager.ts` | 947 | PID 文件管理、进程 spawn、孤儿清理 |
| `src/services/infrastructure/HealthMonitor.ts` | 216 | 端口检测、健康轮询、版本校验 |
| `src/services/infrastructure/GracefulShutdown.ts` | 111 | 优雅关闭流程（6 步级联） |
| `src/supervisor/index.ts` | 193 | Supervisor 单例，管理进程注册表 |
| `src/supervisor/process-registry.ts` | 287 | 进程注册表，JSON 持久化 |
| `src/supervisor/shutdown.ts` | 157 | 级联关闭（SIGTERM → 等待 → SIGKILL） |
| `src/services/worker-service.ts` | 1255 | Worker 主体，编排所有子服务 |

---

## 关键流程

### 1. Hook 触发 → 确保 Worker 运行（`worker-spawner.ts` L103-207）

```
hook 触发
  → ensureWorkerStarted(port, scriptPath)
    → cleanStalePidFile()           // 清理僵尸 PID
    → waitForHealth(port, 1s)       // 快速健康检查
    → isPortInUse(port)             // 端口占用检测
    → spawnDaemon(scriptPath, port) // 实际 spawn
    → waitForHealth(port, timeout)  // 等待启动
    → touchPidFile()                // 更新 PID 文件时间戳
```

**关键点**：hook 只做"确保 worker 存在"，不做引用计数。多个 hook 并发调用时，通过 PID 文件 + `cleanStalePidFile()` 避免重复 spawn。

### 2. Worker 自写 PID（`worker-service.ts` L318-333）

```typescript
// Worker 写自己的 PID（不是 spawner 写的，因为 Windows 上 spawner 的 PID 是 cmd.exe）
writePidFile({
  pid: process.pid,
  port,
  startedAt: new Date().toISOString()
});

getSupervisor().registerProcess('worker', {
  pid: process.pid,
  type: 'worker',
  startedAt: new Date().toISOString()
});
```

### 3. Windows 孤儿进程检查（`ProcessManager.ts` L52-73）

```typescript
// Windows 上 PID 可能被回收（recycled），所以要验证进程名
export function isWorkerPid(pid: number): boolean {
  if (!isPidAlive(pid)) return false;
  if (process.platform !== 'win32') return true;
  // Windows: 验证进程名是 bun.exe（不是 Edge/Chrome 回收的 PID）
  const output = execSync(`wmic process where ProcessId=${pid} get Name /value`, ...);
  const match = output.match(/Name\s*=\s*(.+)/i);
  return name === 'bun.exe' || name === 'bun';
}
```

### 4. 孤儿清理机制（`ProcessManager.ts` L370-487, L506-643）

有两套清理：

- **普通清理** `cleanupOrphanedProcesses()`：30 分钟阈值，只清理超龄进程
- **激进清理** `aggressiveStartupCleanup()`：worker 启动时立即清理 `worker-service.cjs` 和 `chroma-mcp`（这些不该比父进程活得久），只有 `mcp-server.cjs` 保留 30 分钟阈值

**关键代码（L36-37）**：
```typescript
const ORPHAN_MAX_AGE_MINUTES = 30;
// ...只杀超过 30 分钟的进程
```

### 5. 优雅关闭级联（`GracefulShutdown.ts` L52-86）

```typescript
export async function performGracefulShutdown(config: GracefulShutdownConfig): Promise<void> {
  // STEP 1: 关闭 HTTP 服务器
  if (config.server) await closeHttpServer(config.server);
  // STEP 2: 关闭活跃 session
  await config.sessionManager.shutdownAll();
  // STEP 3: 关闭 MCP 客户端
  if (config.mcpClient) await config.mcpClient.close();
  // STEP 4: 停止 Chroma MCP
  if (config.chromaMcpManager) await config.chromaMcpManager.stop();
  // STEP 5: 关闭数据库
  if (config.dbManager) await config.dbManager.close();
  // STEP 6: Supervisor 处理子进程终止 + PID 清理
  await stopSupervisor();
}
```

### 6. Supervisor 级联关闭（`shutdown.ts` L22-76）

```typescript
export async function runShutdownCascade(options: ShutdownCascadeOptions): Promise<void> {
  // Phase 1: SIGTERM 所有子进程
  for (const record of childRecords) {
    await signalProcess(record.pid, 'SIGTERM');
  }
  // 等待 5 秒
  await waitForExit(childRecords, 5000);

  // Phase 2: SIGKILL 存活者（Windows 用 taskkill /F /T）
  const survivors = childRecords.filter(r => isPidAlive(r.pid));
  for (const record of survivors) {
    await signalProcess(record.pid, 'SIGKILL');
  }
  // 等待 1 秒

  // Phase 3: 清理注册表 + 删除 PID 文件
  for (const record of childRecords) {
    options.registry.unregister(record.id);
  }
  rmSync(pidFilePath, { force: true });
  options.registry.pruneDeadEntries();
}
```

### 7. Session 结束时的孤儿收割（`process-registry.ts` L185-264）

```typescript
// session 删除时，杀掉该 session 的所有子进程
async reapSession(sessionId: string | number): Promise<number> {
  const sessionRecords = this.getBySession(sessionId);
  // SIGTERM → 等 5 秒 → SIGKILL → 注销
  // ...同上的 SIGTERM → SIGKILL 流程
}
```

---

## 你的引用计数方案应该改哪里

现有架构中，**缺的是 session 连接/断开的计数**。如果要加引用计数 + 30 分钟延迟回收，需要改的核心位置：

### 入口：`worker-spawner.ts` 的 `ensureWorkerStarted()`

当前逻辑：检测到 worker 存在就 return true，不跟踪"谁在用"。

**改成**：每次调用时递增引用计数。

### 出口：hook 的 SessionEnd

当前逻辑：session 结束时什么都不做（worker 继续跑）。

**改成**：递减引用计数，ref=0 启动 30 分钟倒计时。

### 存储：`ProcessManager.ts` 的 PID 文件

当前格式：
```json
{ "pid": 22752, "port": 37777, "startedAt": "2026-04-13T..." }
```

**改成**：加上引用计数 + 倒计时信息：
```json
{
  "pid": 22752,
  "port": 37777,
  "startedAt": "2026-04-13T...",
  "refCount": 2,
  "shutdownScheduledAt": null
}
```

### 倒计时管理：新建或扩展 `ProcessManager.ts`

需要一个定时器检查：
- refCount == 0 且超过 30 分钟 → 触发 `performGracefulShutdown()`
- refCount > 0 → 取消倒计时

### 替代 `cleanupOrphanedProcesses()`

引用计数准确的话，30 分钟孤儿清理可以去掉，变成更优雅的"最后一个 session 断开后 30 分钟自动关闭"。

---

## Windows 特殊处理备注

- **PID 回收**：Windows 上 PID 很快被回收，必须用 `wmic` 验证进程名（L52-73）
- **僵尸端口**：子进程继承了 socket handle，父进程退出后端口不释放（L48-49 GracefulShutdown.ts）
- **PowerShell spawn**：用 `Start-Process -WindowStyle Hidden` 避免弹窗（L721-748 ProcessManager.ts）
- **spawn 冷却**：失败后 2 分钟内不重试，避免反复弹窗（L39 worker-spawner.ts）

---

## 补充：Hook 层实际调用链

### SessionStart（`src/cli/handlers/session-init.ts`）

Hook 事件：`UserPromptSubmit`

```
Claude Code 触发 UserPromptSubmit hook
  → sessionInitHandler.execute(input)
    → ensureWorkerRunning()                     // 纯 HTTP 健康检查，不 spawn
    → workerHttpRequest('/api/sessions/init')   // 创建/恢复 session
    → workerHttpRequest('/sessions/{id}/init')  // 启动 SDK agent（非 Cursor）
    → workerHttpRequest('/api/context/semantic') // 语义注入（可选）
```

**关键点**：`ensureWorkerRunning()` 只做 `isWorkerHealthy()`（单次 HTTP 检查），不 spawn。spawn 责任在 SessionStart hook（`src/cli/handlers/context.ts`）调用 `ensureWorkerStarted()` 时触发。

### SessionEnd（`src/cli/handlers/session-complete.ts`）

Hook 事件：Session 结束后

```
Claude Code 触发 SessionComplete hook
  → sessionCompleteHandler.execute(input)
    → ensureWorkerRunning()                          // 确认 worker 存在
    → workerHttpRequest('/api/sessions/complete')    // POST，从 active map 移除 session
```

**关键点**：session-complete **只做清理 session 数据**，不通知 worker "我走了"。worker 不知道有多少 session 还在用。这就是缺引用计数的根源。

### 确保 Worker 运行：两层机制

1. **`ensureWorkerRunning()`**（`src/shared/worker-utils.ts` L212-229）
   - 轻量级：单次 HTTP `/api/health` 检查
   - 失败就返回 false，不 spawn
   - hook handlers 用这个

2. **`ensureWorkerStarted()`**（`src/services/worker-spawner.ts` L103-207）
   - 重量级：PID 检查 → 端口检查 → spawn → 等待健康
   - SessionStart hook（`context.ts`）用这个来首次启动 worker

---

## 补充：worker-wrapper.cjs 的作用

`plugin/scripts/worker-wrapper.cjs` 是一个**极简的进程包装器**（minified 约 2 行），源码逻辑如下：

```
wrapper 进程
  → spawn(child: worker-service.cjs, { ipc: true, env: { CLAUDE_MEM_MANAGED: "true" } })
  → 监听 IPC 消息:
      "restart" → kill child → exit(0) → hook 会重新 spawn
      "shutdown" → kill child → exit(0)
  → 监听 child exit:
      非预期退出 → wrapper 也 exit(0)（hook 会重启）
  → 监听 SIGTERM/SIGINT:
      → kill child (Windows: taskkill /T /F, Unix: SIGTERM → 5s → SIGKILL)
      → exit(0)
```

**设计意图**：wrapper 给 worker-service.cjs 包了一层 IPC 控制面。worker 内部可以通过 `process.send({ type: 'restart' })` 请求重启自己。wrapper 的 PID 被 supervisor 注册，wrapper 负责 kill 整个进程树（解决 Windows 僵尸端口问题）。

**CLAUDE_MEM_MANAGED="true"** 环境变量告诉 worker 它被 wrapper 管理了（worker 内部可以据此调整行为）。

---

## 补充：MCP Server 如何感知 Worker

MCP server（`src/servers/mcp-server.ts`）运行在 Node 下，通过 `ensureWorkerStarted()` 感知 worker：

```typescript
// mcp-server.ts 启动时
import { ensureWorkerStarted } from '../services/worker-spawner.js';
const WORKER_SCRIPT_PATH = resolve(mcpServerDir, 'worker-service.cjs');

// 每次 MCP 工具调用前，确保 worker 存在
await ensureWorkerStarted(port, WORKER_SCRIPT_PATH);
```

**特点**：
- MCP server 在 Node 下运行，但 worker 需要 Bun（因为 `bun:sqlite`）
- `ensureWorkerStarted()` 内部会解析 Bun 路径并通过 PowerShell spawn worker
- MCP server 只是 HTTP 客户端，通过 `workerHttpRequest()` 调用 worker API
- MCP server 不直接管理 worker 生命周期，只是"确保它存在"

---

## 更新后的文件清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `src/services/worker-spawner.ts` | 207 | Worker spawn 入口（含 PID/端口/健康检查） |
| `src/services/infrastructure/ProcessManager.ts` | 947 | PID 文件、spawn、孤儿清理、进程名验证 |
| `src/services/infrastructure/HealthMonitor.ts` | 216 | 端口检测、健康轮询、版本校验 |
| `src/services/infrastructure/GracefulShutdown.ts` | 111 | 6 步级联优雅关闭 |
| `src/supervisor/index.ts` | 193 | Supervisor 单例 |
| `src/supervisor/process-registry.ts` | 287 | 进程注册表（JSON 持久化） |
| `src/supervisor/shutdown.ts` | 157 | 级联关闭（SIGTERM → SIGKILL） |
| `src/services/worker-service.ts` | 1255 | Worker 主体（编排所有子服务） |
| `src/shared/worker-utils.ts` | 230 | HTTP 工具函数（ensureWorkerRunning、workerHttpRequest） |
| `src/cli/handlers/session-init.ts` | 175 | SessionStart hook handler |
| `src/cli/handlers/session-complete.ts` | 67 | SessionEnd hook handler |
| `src/servers/mcp-server.ts` | ~800 | MCP Server（Node 进程，HTTP 客户端） |
| `plugin/scripts/worker-wrapper.cjs` | 2（minified） | wrapper 层（IPC + 进程树 kill） |

---

## 完整生命周期时序图

```
用户打开 Claude Code
  │
  ├─ SessionStart hook 触发
  │   ├─ ensureWorkerStarted()          ← 首次 spawn worker
  │   │   └─ PowerShell Start-Process → bun worker-service.cjs --daemon
  │   │       └─ worker 写 PID 文件 + 注册 supervisor
  │   └─ session-init handler
  │       └─ POST /api/sessions/init    ← 创建 session
  │
  ├─ UserPromptSubmit hook（每次对话）
  │   └─ ensureWorkerRunning()          ← 只做健康检查
  │       └─ session-init handler
  │           └─ POST /api/sessions/init ← 更新 session + 语义注入
  │
  ├─ PostToolUse hook
  │   └─ observation handler
  │       └─ POST /api/sessions/observe ← 捕获工具调用
  │
  ├─ Summary hook
  │   └─ POST /api/sessions/summarize   ← 排队 AI 压缩
  │
  ├─ SessionEnd hook
  │   └─ POST /api/sessions/complete    ← 移除 active session
  │       ※ worker 继续运行！不知道没人用了
  │
  ├─ 30 分钟后（如果没人用）
  │   └─ 孤儿清理器检测到超龄进程 → 杀掉  ← 兜底机制
  │
  └─ 下次用户打开 Claude Code
      └─ ensureWorkerStarted()           ← 可能复用仍在跑的 worker
```
