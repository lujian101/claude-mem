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

## F8：版本号不变 marketplace 不重新拉取文件
