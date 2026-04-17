# 研究发现

> claude-mem fork 管理相关技术发现

---

## F1: Marketplace 机制分析（已通过官方文档确认）

### 核心结论：品牌替换完全不必要

根据 Claude Code 官方文档 [Plugin Marketplaces](https://code.claude.com/docs/en/plugin-marketplaces)：

1. **插件下载源不是 `homepage` 字段**，而是用户添加 marketplace 时指定的仓库地址：
   - `/plugin marketplace add lujian101/claude-mem` → 从 lujian101 仓库克隆
   - 与 marketplace.json 中的 `name` 或 `homepage` 无关！

2. **`name` 字段只是标识符**（kebab-case），用于显示和本地引用（如 `plugin install xxx@marketplace-name`），不影响下载源。

3. **`source` 字段决定插件位置**：
   - `"source": "./plugin"` = 仓库内的相对路径（当前方案）
   - 也可以指向外部 GitHub repo、git URL、npm 包等

4. **`CLAUDE_PLUGIN_ROOT` 在运行时总是设置的**：
   > "use this variable in hooks and MCP server configs to reference files within the plugin's installation directory. This is necessary because plugins are copied to a cache location when installed."
   - hooks.json 中的硬编码 fallback 路径几乎不会触发

5. **`CLAUDE_PLUGIN_DATA`** 用于需要跨版本持久化的数据。

### marketplace.json 各字段真实作用

```json
{
  "name": "thedotmack",         // 仅标识符，显示用，不影响功能
  "owner": { "name": "..." },   // 显示用
  "metadata": {
    "description": "...",        // 显示用
    "homepage": "https://..."   // 显示用，不是下载源！
  },
  "plugins": [{
    "name": "claude-mem",
    "source": "./plugin",        // 仓库内相对路径，这才是真正的插件位置
    "version": "10.6.3"
  }]
}
```

### 实际下载流程

```
用户执行: /plugin marketplace add lujian101/claude-mem
    ↓
Claude Code: git clone https://github.com/lujian101/claude-mem
    ↓
读取: .claude-plugin/marketplace.json
    ↓
找到: plugins[0].source = "./plugin"
    ↓
复制: <repo>/plugin/ → ~/.claude/plugins/cache/<marketplace-name>/claude-mem/<version>/
    ↓
设置: CLAUDE_PLUGIN_ROOT = 上述 cache 路径
```

### 结论

**只需修改 1 个文件中的 1-2 个字段**：
- `marketplace.json` → `metadata.homepage` 改为 fork URL（纯显示用）
- 可选：`owner.name` 改为自己

**44 个文件的品牌替换全部可以回退**，不影响任何功能。

---

## F2: 本地修改分类

### 类别 A：纯品牌替换（44 个文件，可回退）

| 文件 | 改动内容 |
|------|---------|
| `.claude-plugin/marketplace.json` | name + homepage |
| `.claude-plugin/plugin.json` | repository URL |
| `plugin/hooks/hooks.json` | 所有路径 thedotmack → lujian101 |
| `scripts/sync-marketplace.cjs` | 所有路径 |
| `scripts/sync-to-marketplace.sh` | 路径 |
| `package.json` | repository/homepage/bugs URLs |
| 其他 38 个文件 | 搜索替换 thedotmack → lujian101 |

**合并影响**：每次合并上游，这些文件都会冲突（因为上游永远用 thedotmack）

### 类别 B：功能修改（需要保留）

| 文件 | 改动内容 |
|------|---------|
| `src/services/worker/OpenRouterAgent.ts` | 国内 LLM 兼容、智能头部控制 |
| `src/shared/SettingsDefaultsManager.ts` | 新增配置项 |
| `src/ui/viewer/` 相关 | UI 适配新配置 |

**合并影响**：中等风险，取决于上游是否动了这些文件

### 类别 C：行为修改（需要保留）

| 文件 | 改动内容 |
|------|---------|
| `plugin/hooks/hooks.json` | 禁用 worker 自动启动 + 简化 PATH |

**合并影响**：高风险，上游经常调整 hooks

### 类别 D：编译产物

| 文件 | 改动内容 |
|------|---------|
| `plugin/scripts/*.cjs` | 编译后包含品牌替换 |
| `plugin/ui/viewer-bundle.js` | 编译后包含品牌替换 |
| `install/public/installer.js` | 编译后 |
| `installer/dist/index.js` | 编译后 |

**合并影响**：编译产物每次 build 都会重新生成，不需要手动维护

---

## F3: 上游 hooks.json vs 本地 hooks.json 差异

### 上游版本特点
1. 设置 nvm/PATH 环境（Linux/macOS 专用）
2. Cache 目录查找 fallback
3. Worker 自动启动 + 健康检查等待
4. SessionStart 包含 3 个 hook（install + start + context）

### 本地版本特点
1. 无 PATH 设置（Windows 不需要 nvm）
2. 无 cache 查找（直接用 marketplace 路径）
3. Worker 不自动启动（手动管理）
4. SessionStart 包含 2 个 hook（install + context）

### 兼容性分析
- 上游的 nvm PATH 设置在 Windows 上会失败，但不影响功能（Windows 有自己的 node 路径）
- Cache 查找是合理的优化，本地可保留
- Worker 自动启动被禁用是用户的选择，需单独维护

---

## F4: 当前落后上游状态

- 落后 upstream/main **165 个 commit**
- 上游版本号已远超本地（本地停留在 10.6.3 的编译版本）
- 需要评估上游是否有 breaking changes

---

## F5: .bat 脚本问题

现有 .bat 脚本：
- `start-worker.bat` - 启动 worker
- `stop-worker.bat` - 停止 worker
- `restart-worker.bat` - 重启 worker
- `status-worker.bat` - 查看状态

**已知问题**：用户反馈"有问题，不好用"，具体问题待分析。后续需要重写或用 npm scripts 替代。

---

## F6: Windows Worker 进程管理痛 `点

> **影响范围**：`process.spawn()` 的 Windows 实现 — 僵尸进程 + 端口占用 + 对话卡住

### 问题 1：Worker 挂了，Hooks 超时卡住对话

**根因**：`worker-utils.ts:fetchWithTimeout()` 里，hook 向 worker 发 HTTP 请求时的默认超时是 `HEALTH_CHECK_TIMEOUT_MS`。

当前超时配置（`hook-constants.ts`）：
```
HEALTH_CHECK: 3000ms → Windows 乘 1.5 = 4500ms
PORT_IN_USE_WAIT: 3000ms → 4500ms
POST_SPAWN_WAIT: 15000ms → 22500ms
READINESS_WAIT: 30000ms → 45000ms
```

但实际调用链：
1. hook 脚本启动（Node/Bun 执行 `plugin/scripts/worker-service.cjs hook claude-code observation`）
2. `hookCommand()` → handler 执行 → `ensureWorkerRunning()`
3. `ensureWorkerRunning()` → `isWorkerHealthy()` → `workerHttpRequest('/api/health')`
4. 这里用 `HEALTH_CHECK_TIMEOUT_MS`（3s/4.5s Windows）
5. 如果 worker 挂了，TCP 连接 `ECONNREFUSED` 会被 `fetchWithTimeout` 捕获
6. `ensureWorkerRunning()` 返回 `false`
7. handler 直接返回空结果 → **不会卡住**

**关键发现**：`ensureWorkerRunning()` 的超时是 3-4.5s，实际上不会卡太久。真正卡的情况是 worker 进程占用端口但不响应（僵尸进程），这时 `fetch` 连接成功但读取超时，等满 4.5s 才返回。

**实际影响**：每次工具调用如果遇到僵尸 worker，会多等 ~4.5 秒。虽然不致命，但体感很明显。

### 问题 2：僵尸进程 + 端口占用（Windows 特有）

**根因**：`worker-service.ts:spawnDaemon()` 在 Windows 上用 `Start-Process -WindowStyle Hidden`。
- `Start-Process` 启动 bun.exe，但 Windows 进程树模型导致：
  - bun.exe 挂了但子进程（SQLite、Chroma Python）还在
  - `taskkill /T /F` 不一定完全清理
  - 端口 37777 仍然被占用（`TIME_WAIT` 或子进程 hold）

**典型场景**：
1. 电脑休眠/网络断开 → worker 内部连接断开 → bun 崩溃
2. bun 崩溃但 SQLite/Python 进程还活着，端口没释放
3. 下次 hook 触发 → `isPortInUse()` 返回 `true` → `waitForHealth()` 超时失败
4. `ensureWorkerStarted()` 因为端口占用无法 spawn 新 worker
5. 用户必须手动 `taskkill` 或重启

**目前的缓解措施**：
- `worker-spawner.ts` 有 Windows 2 分钟 spawn cooldown（防止弹窗循环）
- `worker-wrapper.cjs` 有进程树清理（`taskkill /T /F`）
- PID 文件 + `isProcessAlive()` 检测
- 但都不够可靠

### 问题 3：进程树模型差异

`spawnDaemon()` 在 Windows 用 PowerShell `Start-Process -WindowStyle Hidden`：
```
Claude Code
  └─ worker-service.cjs hook claude-code observation (hook 进程)
       └─ PowerShell Start-Process
            └─ bun.exe worker-service.cjs --daemon (worker 进程)
                 └─ child processes (SQLite, Python Chroma)
```

问题是 hook 进程退出后，中间的 PowerShell 进程也退出了，但 bun.exe 树可能残留。

### 可能的优化方案

#### 方案 A：缩短 hook 端超时（低成本）
- `HEALTH_CHECK` 从 3s 降到 1s（正常 worker 响应 <100ms）
- 僵尸进程检测用 TCP connect 而非 fetch（connect 失败立刻知道端口没服务）
- 风险小，改动少

#### 方案 B：增加 TCP 连接探活（中等成本）
- 在 `fetchWithTimeout()` 前先做 TCP socket connect 探活
- `net.connect(port)` 超时 200ms，如果连接被拒绝（`ECONNREFUSED`）直接返回 worker 不可用
- 避免等 `fetch` 走完完整超时
- 需要改 `worker-utils.ts`

#### 方案 C：Windows 端口释放机制改进（中等成本）
- 在 `isPortInUse()` 检测到端口被占用但 worker 不健康时
- 自动查找占用端口的进程 PID 并尝试 kill
- 用 `netstat -ano | findstr :37777` 找 PID
- 结合 PID 文件交叉验证，如果不是同一个 PID 则尝试 kill

#### 方案 D：Worker 健康自检 + 自动重启（高成本）
- worker 内部增加 watchdog，定期自检
- 检测到内部异常（DB 连接断、Chroma 超时）主动退出
- hook 侧检测到 worker 挂了自动触发重启
- 与现有 `ensureWorkerStarted()` 配合

#### 推荐组合
1. **先做方案 B**（TCP 探活）— 解决"连接僵尸进程等超时"问题
2. **再做方案 C**（端口清理）— 解决"端口占用无法重启"问题
3. 方案 A 可以和 B 一起做

### Windows 适配注意事项

- `AbortSignal.timeout()` 在 Bun + Windows 上会导致 libuv assertion crash（已在 `fetchWithTimeout()` 中绕过）
- PowerShell `Start-Process` 的 PID 返回的是 PowerShell 进程 PID，不是 bun.exe 的 PID（worker 需要自己写 PID 文件）
- `taskkill /T /F` 在某些情况下杀不掉进程树（特别是非 cmd.exe 启动的子进程）
- 端口 `TIME_WAIT` 状态在 Windows 上默认持续 4 分钟

### 已实施修复：PID 回收验证（2026-04-13）

#### 问题根因

Windows 的 PID 回收机制导致 `isProcessAlive(pid)` 误判：

```
Worker 崩溃 (bun.exe PID=19760)
    → PID 19760 被系统回收分配给 Edge
    → PID 文件里还写着 19760
    → isProcessAlive(19760) → process.kill(19760, 0) → true (Edge 确实活着)
    → 误判为 "worker 还活着"
    → 新 worker 无法启动
```

本机实测复现：PID 19760 占着端口 37777 LISTENING，但实际是 Edge 浏览器的进程。curl 连接超时不响应。

#### 修复方案

在 `isProcessAlive()` 基础上增加 **进程名验证**：

**新增函数**：
- `src/supervisor/process-registry.ts` → `isWorkerPid(pid)` 
- `src/services/infrastructure/ProcessManager.ts` → `isWorkerProcessAlive(pid)`

**验证逻辑**：
1. `process.kill(pid, 0)` — PID 是否存在
2. Windows 上额外执行 `wmic process where ProcessId=X get Name /value`
3. 解析输出 `Name=bun.exe`，确认是 bun 进程
4. 如果 PID 被 Edge/Chrome 回收 → 名字对不上 → 返回 `false`
5. Unix 不做额外检查（PID 回收概率极低）
6. wmic 失败时 fallback 到基础检查（保守策略）

**修改点**：

| 文件 | 改动 |
|------|------|
| `src/supervisor/process-registry.ts` | 新增 `isWorkerPid()` |
| `src/services/infrastructure/ProcessManager.ts` | 新增 `isWorkerProcessAlive()` |
| `src/supervisor/index.ts` | `validateWorkerPidFile()` 改用 `isWorkerPid()` |
| `src/services/worker-service.ts` | GUARD 1 改用 `isWorkerProcessAlive()` |

**局限**：只解决了 PID 回收误判问题。端口残留（进程死了但端口还在 LISTENING）是独立问题，需要方案 C（端口清理）来解决。

## F7：Marketplace 安装文件行尾差异（CRLF vs LF）

**发现时间**：2026-04-13
**现象**：marketplace 安装目录的构建产物（.cjs）hash 与本地项目不同
**原因**：`core.autocrlf=true` 导致 git checkout 时部分行被转成 CRLF，本地构建产物保持 LF
**验证**：`diff --strip-trailing-cr` 确认内容完全一致，纯行尾差异
**影响**：无，功能完全等价，不需要处理

## F8：Bun/Windows fetch() 阻塞事件循环（2026-04-15 关键发现）

**严重程度**：🔴 高 — 导致对话卡死 20+ 分钟

### 根因

Bun 在 Windows 上，当 `fetch()` 连接的目标端口没有进程监听时，底层 TCP connect 通过 IOCP 发出后**没有正确返回事件给 libuv**：

1. `fetch()` 底层 TCP 操作阻塞了 libuv 事件循环
2. `setTimeout` 的回调永远排不上队（因为事件循环被卡住了）
3. Promise.race 的两个分支都挂了
4. Hook 进程永久等待

### 受影响的代码路径

| 文件 | 函数 | 问题 |
|------|------|------|
| `worker-utils.ts` | `fetchWithTimeout()` | Promise.race 的 setTimeout 无法触发 |
| `HealthMonitor.ts:27` | `httpRequestToWorker()` | **裸 fetch() 完全无超时** — 所有 CLI 命令卡死根源 |
| `HealthMonitor.ts:54` | `isPortInUse()` Windows 分支 | **裸 fetch() 完全无超时** |
| `HealthMonitor.ts:140` | `httpShutdown()` | **裸 fetch() 完全无超时** |

### 为什么 safety timer 能兜底

Safety timer 在 `fetch()` 调用**之前**就已注册到事件循环。只要 Bun 进程本身没死，timer 一定会触发（Bun 的事件循环是协作式的，timer 注册在 fetch 之前）。

### 已实施修复

| 修复 | 文件 | 效果 |
|------|------|------|
| 进程级 safety timer | `hook-command.ts` | hook 30s 硬上限，超时弹 Toast + exit(0) |
| Toast 提醒 | `worker-utils.ts` | 手动模式下 worker 不可达弹通知 |
| worker-cli.js 脚本 | `~/.claude-mem/worker-*.bat` | 用 process.kill(pid,0) 而非 HTTP，不卡 |

### 未修复（下一步）

- `HealthMonitor.ts` 的 3 个裸 fetch() 调用 — 需要加超时（全面修复方案）

## F9：worker-cli.js vs worker-service.cjs CLI（2026-04-15）

### 关键差异

| 维度 | worker-service.cjs CLI | worker-cli.js |
|------|----------------------|---------------|
| status 检查 | `isPortInUse()` → 裸 fetch → **卡死** | `process.kill(pid, 0)` → 系统调用 → **秒返** |
| start 方式 | `ensureWorkerStarted()` → 完整 spawn 流程 | `ProcessManager.start()` → PowerShell Start-Process |
| stop 方式 | `httpShutdown()` → 裸 fetch → 可能卡 | HTTP + AbortSignal.timeout + taskkill 兜底 |
| 适合场景 | worker 自身的 CLI 入口 | 外部管理脚本调用 |

### 路径

- worker-service.cjs: `cache/thedotmack/claude-mem/12.1.0/scripts/worker-service.cjs`
- worker-cli.js: `cache/thedotmack/claude-mem/12.1.0/scripts/worker-cli.js`

### 结论

**管理脚本必须用 worker-cli.js**，worker-service.cjs 的 CLI 会因为裸 fetch 在 Bun/Windows 上卡死。

## F10：Worker 启动失败（2026-04-15 待排查）

### 现象

`bun worker-cli.js start` 后 worker 立即退出：

```
[wrapper] Spawning inner worker: .../worker-service.cjs
[wrapper] Inner exited with code=0, signal=null
[wrapper] Inner exited unexpectedly, wrapper exiting
```

### 可能原因

1. **isPluginDisabledInClaudeSettings()** — worker-service.cjs main() 无参数时检查此函数，可能返回 true
2. **端口残留** — netstat 显示 37777 有 5 个 FIN_WAIT_2 连接
3. **wrapper 路径** — worker-cli.js 硬编码 marketplace 路径而非 cache 路径

### 待排查

- [ ] 检查 Claude settings.json 里 claude-mem 是否被禁用
- [ ] 检查 FIN_WAIT_2 连接是否阻止 listen()
- [ ] 检查 wrapper 传递的参数和环境变量

## F11：Managed 模式 Shutdown 跳过 Graceful Cleanup（2026-04-16 关键发现）

**严重程度**：🔴 高 — 每次关闭 worker 都会产生僵尸端口

### 根因

`Server.ts:266` 的 `/api/admin/shutdown` 处理逻辑分两条路径：

```js
if (isWindowsManaged) {
  process.send({ type: 'shutdown' });  // 只发 IPC，不做 cleanup
} else {
  setTimeout → performGracefulShutdown() → process.exit(0)
}
```

Managed 模式（`CLAUDE_MEM_MANAGED=true`，wrapper 启动）直接发 IPC 让 wrapper 用 `taskkill /T /F` 硬杀进程，**完全跳过** `performGracefulShutdown()`。

### 僵尸端口形成的完整因果链

1. `POST /api/admin/shutdown` → managed 模式直接发 IPC 给 wrapper
2. Wrapper 收到后 `taskkill /T /F` 硬杀 worker 进程
3. `taskkill /T` **没有杀干净 Chroma 子进程树**（uvx → uv → chroma-mcp → python），变成孤儿
4. 孤儿进程继承了 listening socket handle → OS 不释放端口 → 僵尸 LISTENING
5. 即使孤儿进程最终死亡，如果 Edge 浏览器有 ESTABLISHED 连接吊着，CLOSE_WAIT/FIN_WAIT_2 会持续数分钟

### 修复（已提交：43fe99d7）

统一两条路径：**始终先执行 `performGracefulShutdown()`**（关 HTTP server、关连接、停子进程），完成后再决定是发 IPC 还是 `process.exit(0)`。

## F12：Auto-Start 守卫不读 settings.json（2026-04-16 关键发现）

**严重程度**：🔴 高 — `WORKER_AUTO_START=false` 完全无效

### 根因

`worker-spawner.ts:ensureWorkerStarted()` 和 `worker-utils.ts:ensureWorkerRunning()` 使用：

```ts
SettingsDefaultsManager.get('CLAUDE_MEM_WORKER_AUTO_START')
```

`get()` 的实现：

```ts
static get(key): string {
    return process.env[key] ?? this.DEFAULTS[key];
}
```

**只检查环境变量和硬编码默认值，根本不读 `~/.claude-mem/settings.json`**。

而 `DEFAULTS.CLAUDE_MEM_WORKER_AUTO_START = 'true'`，所以永远返回 `'true'`。

### 修复（已提交：676732c3）

改用 `SettingsDefaultsManager.loadFromFile(USER_SETTINGS_PATH)`，走完整优先级链：
`env > settings file > default`

### 影响范围

`SettingsDefaultsManager.get()` 的其他调用点：
- `CLAUDE_MEM_DATA_DIR` — 构建 settings 路径本身，不能循环依赖，用 `get()` 正确
- `CLAUDE_MEM_HOOK_TOTAL_TIMEOUT_MS` — hook 最早初始化阶段，env 覆盖够用，用 `get()` 正确
- `CLAUDE_MEM_WORKER_AUTO_START` — **唯一需要读 settings.json 的场景**，已修复

## F13：taskkill /T 无法杀干净 Chroma 子进程树（2026-04-16 发现）

**严重程度**：🟡 中 — 配合 F11 的修复，graceful shutdown 会先停 Chroma，此问题影响降低

### 现象

Worker 通过 `uvx` 启动 Chroma，形成 4 层进程树：

```
wrapper (PID 1560) [已死]
  └─ uvx.exe (PID 9096)
       └─ uv.exe (PID 12176)
            └─ chroma-mcp.exe (PID 22384)
                 └─ python.exe (PID 22408)
                      └─ python.exe (PID 22424)
```

Wrapper 执行 `taskkill /PID <worker> /T /F` 后，这整条 Chroma 链变成孤儿，未被杀掉。这些进程可能继承了 listening socket handle，阻止 OS 释放端口 37777。

### 影响

- 即使 worker 进程已死，孤儿 Chroma 进程保持 socket handle 活着
- 杀掉所有孤儿后，端口在 3 秒内释放（实测确认）

### 缓解

F11 的修复（先 graceful shutdown 再 IPC）会在 wrapper taskkill 之前关闭 Chroma 连接（`performGracefulShutdown` Step 4: `chromaMcpManager.stop()`），大幅降低孤儿进程概率。但 wrapper 的 `d()` 函数仍应改进进程树遍历可靠性。

## F14：Cache 目录未同步导致修复无效（2026-04-17 发现）

**严重程度**：🔴 高 — 所有本地修复都没生效

### 根因

用户在项目源码中做了多个修复（F11-F13），编译后的 `worker-service.cjs` 也已更新到 `plugin/scripts/`，但 **从未同步到 Claude Code 实际运行的两个目录**：

- `~/.claude/plugins/cache/thedotmack/claude-mem/12.1.0/scripts/` — hooks 调用路径
- `~/.claude/plugins/marketplaces/thedotmack/plugin/scripts/` — worker-cli.js/wrapper 调用路径

两个目录都还是旧版 `worker-service.cjs`，所有修复（auto-start 守卫读 settings.json、graceful shutdown、僵尸端口清理、HealthMonitor 超时）完全无效。

### 影响范围

| 修复 | 状态 |
|------|------|
| F11: managed shutdown graceful cleanup | 源码有，cache 无 |
| F12: auto-start 守卫读 settings.json | 源码有，cache 无 |
| F13: 僵尸端口 cleanupZombiePort | 源码有，cache 无 |
| HealthMonitor AbortSignal 超时 | 源码有，cache 无 |

### 教训

**每次 build 后必须同步到 cache + marketplace 两个目录**。`build-sync.py` 应该自动处理。

## F15：Worker PID 文件冲突 — wrapper PID vs inner worker PID（2026-04-17 关键发现）

**严重程度**：🔴 高 — managed 模式下 worker 无法启动

### 根因

`worker-cli.js` 的 `ProcessManager.start()` 通过 PowerShell `Start-Process` 启动 wrapper，PowerShell 返回的是 **wrapper 进程的 PID**。`worker-cli.js` 立即将这个 PID 写入 `worker.pid` 文件。

随后 wrapper 启动 inner worker（`worker-service.cjs`），inner worker 进入 `default` case 的 GUARD 1：

```ts
const existingPidInfo = readPidFile();
if (existingPidInfo && isWorkerProcessAlive(existingPidInfo.pid)) {
    process.exit(0);  // "Worker already running"
}
```

PID 文件里存的是 **wrapper 的 PID**，而 wrapper 是 inner worker 的父进程，当然活着。Inner worker 误判为"已有 worker 在跑"，立即退出。

同样的问题也存在于 `supervisor/index.ts:41-43`：

```ts
const pidStatus = validateWorkerPidFile({ logAlive: false });
if (pidStatus === 'alive') {
    throw new Error('Worker already running');
}
```

### 修复（已实施）

两处检查都在 managed 模式下跳过：

1. `worker-service.ts` GUARD 1 — `if (!isManaged)` 包裹
2. `supervisor/index.ts` start() — `if (CLAUDE_MEM_MANAGED !== 'true')` 包裹

**文件**：`src/services/worker-service.ts`、`src/supervisor/index.ts`

## F16：isPluginDisabledInClaudeSettings 阻止手动管理工具启动（2026-04-17 发现）

**严重程度**：🟡 中 — 插件禁用时无法通过管理脚本手动启动 worker

### 根因

`worker-service.ts:1046` 的 disabled 检查拦截了所有 hook-initiated 命令（包括 `undefined`，即 wrapper 无参调用）。当 `enabledPlugins: {"claude-mem@thedotmack": false}` 时，手动管理脚本也无法启动 worker。

### 修复（已实施）

`worker-manage.py` 在 `start` 时注入 `CLAUDE_MEM_MANUAL_START=true` 环境变量。`worker-service.ts` 的检查改为：

```ts
if (...&& isPluginDisabledInClaudeSettings()
    && process.env.CLAUDE_MEM_MANUAL_START !== 'true') {
    process.exit(0);
}
```

环境变量穿透链路：Python subprocess → bun → PowerShell Start-Process → wrapper → inner worker（实测验证成功）。

**文件**：`~/.claude-mem/worker-manage.py`、`src/services/worker-service.ts`

## F17：performGracefulShutdown 被 catch 吞异常导致 Chroma 未关闭（2026-04-17 关键发现）

**严重程度**：🔴 高 — 每次关闭 worker 都会产生僵尸端口

### 根因

`Server.ts:266-287` 的 shutdown 路由：

```ts
setTimeout(async () => {
    try {
        await this.options.onShutdown();  // performGracefulShutdown
    } catch {
        // Shutdown may partially fail; we still need to exit cleanly.
        // ← 异常被静默吞掉！
    }
    if (process.env.CLAUDE_MEM_MANAGED === 'true' && process.send) {
        process.send!({ type: 'shutdown' });  // 立即发 IPC
    }
}, 100);
```

`performGracefulShutdown` 的 STEP 1 (`closeHttpServer`) 在 Bun/Windows 上可能抛异常：
- `server.closeAllConnections()` — Bun API 兼容性问题
- `server.close()` + Windows delay

异常被 catch 吞掉后，STEP 2-6（包括 **STEP 4: Chroma MCP stop**）全部跳过。接着 IPC 发给 wrapper，wrapper taskkill 杀进程 → Chroma 子进程变孤儿 → 继承 socket handle → 僵尸 LISTENING 端口。

### 日志证据

```
[12:10:07.040] Shutdown initiated                    ← STEP 1 开始
[04:10:07.585] shutdown requested by inner           ← IPC 已发（545ms 后）
[04:10:07.830] taskkill completed                    ← wrapper 杀进程
```

STEP 1 在 Windows 上需要 1000ms（两个 500ms delay），但只过了 545ms 就发了 IPC，说明异常提前终止了 shutdown。

### 推荐修复方向

1. **A) 修 shutdown**：给 catch 加错误日志，修复 `closeHttpServer` 在 Bun 上的兼容性，确保每个 STEP 独立 try/catch
2. **B) 修 wrapper**：让 wrapper 在 taskkill 后额外查找并清理 Chroma 子进程树（更健壮的兜底）
3. **C) 两者都做**：A 修根因 + B 兜底

## F18：worker-manage.py subprocess.run 未传 env 参数（2026-04-17 关键发现）

**严重程度**：🔴 高 — 手动管理脚本完全无法启动 worker

### 现象

`worker-start.bat` 调用 `worker-manage.py start`，输出：

```
Failed to start: Process died during startup
```

Wrapper 日志显示 inner worker 立即 exit(0)。

### 排查过程

1. 直接用 `bun worker-cli.js start` 启动成功 → 问题在 Python 调用层
2. 逐步缩小：Python `-c` 内联代码成功，Python 文件脚本失败
3. 创建多版本文逐步对比，锁定差异在 `subprocess.run` 参数
4. 注入 preload debug 脚本到 marketplace worker-service.cjs，确认 inner worker 收到 `MANUAL_START="undefined"`

### 根因

`worker-manage.py` 设置了 `env["CLAUDE_MEM_MANUAL_START"] = "true"`，但调用时：

```python
# 修复前 — env 从未传给子进程
subprocess.run(["bun", str(cli), action])

# 修复后
subprocess.run(["bun", str(cli), action], env=env)
```

没有 `env=env`，Python 的 `subprocess.run` 使用默认的 `os.environ`，不包含新添加的变量。

### 排查方法论总结

Env 传递问题排查黄金法则：**在目标进程内部直接观测**。外部测试（bash 直接设 env）可能绕过问题路径。本次通过注入 preload 脚本到 marketplace 的 worker-service.cjs 才最终定位到 env 丢失。

**Env 传递全链路**：Python `env=` → bun `process.env` → `spawnSync` 继承 → PowerShell 继承 → `Start-Process` 继承 → wrapper `...process.env` 展开 → inner worker `process.env`

### 修复

- `worker-manage.py`：添加 `import os` + `subprocess.run(..., env=env)`
- 已验证：`cmd.exe → python → worker-manage.py start` 完整路径通过
