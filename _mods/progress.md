# 会话进度日志

---

## 2026-04-13 — Fork 管理体系搭建

### 完成事项

**阶段一：Marketplace 机制研究**
- [x] 分析项目当前状态（git diff, remote 配置, 本地修改清单）
- [x] 识别三大类本地修改：品牌替换(44文件) / OpenRouter 兼容(5文件) / Worker 管理(hooks)
- [x] 通读 Claude Code 官方文档 plugin-marketplaces.md
- [x] 确认 Marketplace source vs Plugin source 两个独立概念
- [x] 结论：marketplace.json 不需要任何修改

**阶段二：文档目录创建**
- [x] 创建 `_mods/` 目录
- [x] 迁移 OPENROUTER_COMPAT_PATCH.md、MANUAL_WORKER_MANAGEMENT.md
- [x] 迁移 .bat 脚本（start/stop/restart/status-worker.bat）
- [x] 编写 `_mods/README.md`（修改点总览）
- [x] 编写 `_mods/marketplace-mechanism.md`（插件机制解析）
- [x] 编写 `_mods/upstream-sync-guide.md`（同步操作手册）

**阶段三：品牌替换回退**
- [x] 创建 `refactor/minimal-fork` 分支
- [x] 批量 sed 替换 lujian101 → thedotmack（30+ 源文件）
- [x] 修正 marketplace.json owner.name 残留（thedotmack → Alex Newman）
- [x] 重新编译插件（build 成功）
- [x] sed 处理 installer 编译产物

**阶段四：上游合并**
- [x] git merge upstream/main（162 commits）
- [x] 解决 6 个冲突：
  - .gitignore → 采用上游
  - hooks.json → 采用上游（含 worker 自动启动 + 健康检查）
  - 4 个编译产物 → 采用上游后重新 build
- [x] OpenRouter 源码文件全部自动合并（零冲突）
- [x] npm install 安装上游新增依赖
- [x] 最终 build 全部成功（含 NPX CLI、OpenClaw、OpenCode 插件）
- [x] force push 到 origin/main

### 关键发现

1. **marketplace.json 完全不需要改** — 安装源由 `/plugin marketplace add` 命令参数决定
2. **CLAUDE_PLUGIN_ROOT 在运行时始终设置** — hooks.json 硬编码路径几乎不触发
3. **44 个文件的品牌替换全部多余** — 原始 thedotmack 路径就是对的
4. **上游 hooks.json 已改进** — 新增健康检查、file-context hook、cache 版本查找

### 当前状态

- 分支：`main`（与远程同步）
- 版本：v12.1.0
- 与上游差异：9 个文件（5 OpenRouter 源码 + 4 编译产物）+ `_mods/` 目录
- 工作区：干净

### 2026-04-13 — Windows Worker PID 回收修复

**已完成**
- [x] 本机测试确认问题：PID 19760 被 Edge 回收，端口 37777 僵尸 LISTENING 不响应
- [x] 代码分析：定位 `isProcessAlive()` 只用 `process.kill(pid, 0)` 不验证进程名
- [x] 实现 `isWorkerPid()` / `isWorkerProcessAlive()` — Windows 上用 wmic 验证进程名是 bun.exe
- [x] 修改 `validateWorkerPidFile()` 和 worker-service GUARD 1 使用新函数
- [x] 编译通过，构建产物已更新
- [x] 文档更新至 `findings.md`（F6 章节）

**待处理**
- [ ] 端口残留清理（方案 C）— 进程死了但端口 LISTENING 残留
- [ ] Hook 端超时优化（方案 B）— TCP 探活缩短僵尸端口场景的等待时间

### 2026-04-15 — Worker 稳定性修复 & 手动管理模式

### 完成事项

**阶段七：Worker 稳定性修复**
- [x] 完整分析 Worker 启动机制（hook → ensureWorkerRunning → spawner）
- [x] 定位卡死根因：Bun/Windows fetch() 阻塞事件循环，fetchWithTimeout 失效
- [x] hook-command.ts 加进程级 safety timer（30s 可配置）+ Windows Toast 通知
- [x] SettingsDefaultsManager 新增 CLAUDE_MEM_WORKER_AUTO_START + CLAUDE_MEM_HOOK_TOTAL_TIMEOUT_MS
- [x] worker-spawner.ts 加 auto-start 配置守卫
- [x] worker-utils.ts 加手动模式 Toast 提醒（5 分钟冷却）
- [x] 修复网页端 OpenRouter Base URL 不保存/不显示（SettingsRoutes + useSettings）
- [x] 创建 worker-start.bat / worker-stop.bat / worker-status.bat
- [x] 修复脚本：改用 worker-cli.js（不走 HTTP 不卡死）
- [x] settings.json 已更新：WORKER_AUTO_START=false, HOOK_TOTAL_TIMEOUT_MS=10000
- [x] 编译成功，推送 GitHub（commit 30d49729）

### 待处理

- [ ] **Worker 启动失败修复** — worker-cli.js start 后 worker 立即退出 (exit 0)
- [ ] **HealthMonitor 超时修复** — httpRequestToWorker / isPortInUse / httpShutdown 三个裸 fetch
- [ ] **集成测试验收** — 手动启动/停止/状态 + Toast 提醒 + Hook 降级
- [ ] **Windows 同步脚本** — 替代 rsync 的 robocopy/xcopy 方案
- [ ] **构建发布流程文档** — bump → build → sync → push 完整流程

### 未完成（历史遗留）

- [ ] 管理技能创建（阶段七）
- [ ] Windows 适配文档
- [ ] .bat 脚本重写（当前有已知问题）
- [ ] 构建发布流程详细文档

### 2026-04-16 — Worker 关键 Bug 修复

**已完成**

- [x] **F11：Managed 模式 Shutdown 跳过 Graceful Cleanup**
  - 根因：Server.ts managed 路径直接 IPC → wrapper taskkill，跳过所有 cleanup
  - 修复：统一两条路径，始终先 `performGracefulShutdown()` 再决定退出方式
  - commit: 43fe99d7

- [x] **F12：Auto-Start 守卫不读 settings.json**
  - 根因：`SettingsDefaultsManager.get()` 只查 env + 默认值，不读 settings.json
  - `WORKER_AUTO_START=false` 写在 settings.json 里完全无效
  - 修复：改用 `loadFromFile(USER_SETTINGS_PATH)` 走完整优先级链
  - commit: 676732c3

- [x] **F13：Chroma 子进程树杀不干净导致僵尸端口**
  - 根因：`taskkill /T /F` 无法杀完 uvx→uv→chroma-mcp→python 4 层进程树
  - 孤儿进程继承 listening socket handle → 端口不释放
  - 杀掉所有孤儿后 3 秒内端口释放（实测确认）
  - F11 修复已缓解（先 graceful shutdown 停 Chroma 再 IPC）

- [x] 8.2 僵尸端口修复（netstat 检测 + cleanupZombiePort）
  - commit: 380668f6

- [x] 8.3 HealthMonitor 超时修复（AbortSignal.timeout）
  - commit: 380668f6

**待处理**

- [x] **同步编译产物到 cache + marketplace 两个目录**（F14 修复）
  - 发现所有修复一直没同步到 Claude Code 实际运行目录
  - cache: `~/.claude/plugins/cache/thedotmack/claude-mem/12.1.0/scripts/`
  - marketplace: `~/.claude/plugins/marketplaces/thedotmack/plugin/scripts/`
  - 已同步，三个位置（项目/cache/marketplace）一致

- [ ] **Wrapper 进程树清理可靠性改进**（F13 后续）
  - wrapper 的 `d()` 函数应改进 Windows 进程树遍历

### 2026-04-17 — Worker 启动/关闭调试

**已完成**

- [x] **F14：Cache 目录未同步** — 发现所有修复从未同步到实际运行目录
  - 每次 build 后必须同步到 cache + marketplace 两个目录
- [x] **F15：Worker PID 文件冲突** — managed 模式下 wrapper PID 导致 GUARD 1 误判
  - 修复：worker-service.ts GUARD 1 + supervisor/index.ts start() 在 managed 模式下跳过 PID 检查
- [x] **F16：手动管理工具绕过 disabled 检查** — CLAUDE_MEM_MANUAL_START 环境变量
  - worker-manage.py 注入 env var → 穿透 Python→bun→PowerShell→wrapper→inner worker
  - 实测验证 env var 成功传递

### 2026-04-17 — Worker 启动/关闭验证 & env 修复

**已完成**

- [x] **3 轮 start/stop/restart 循环测试** — 全部通过，零失败
  - 每轮：start → 验证 health → stop → 验证端口释放 → restart → 验证
  - PID 每次更新，端口每次干净释放，无僵尸进程

- [x] **F18：worker-manage.py env 传递丢失**（关键发现）
  - 现象：`worker-start.bat` 报 "Process died during startup"，wrapper 日志显示 inner worker exit=0
  - 排查：注入 preload debug 脚本到 inner worker，发现 `MANUAL_START="undefined"`
  - 根因：`worker-manage.py` 的 `subprocess.run(["bun", ...])` **没有传 `env=env` 参数**
  - 虽然代码里 `env["CLAUDE_MEM_MANUAL_START"] = "true"` 但从不传给子进程
  - 修复：添加 `env=env` 参数到 `subprocess.run()`
  - **排查经验**：Env 传递问题需要逐层验证（Python→bun→PowerShell→wrapper→inner），用 preload 脚本注入是最直接的调试方法

- [x] **TypeScript 编译错误修复**（5 类 10 处 Error）
  - `logger.ts`：`'TRANSCRIPT'` 加入 Component 联合类型
  - `worker-service.ts`：`ensureWorkerStarted` → `ensureWorkerStartedShared`（参数数量不匹配）
  - `worker-service.ts`：`sseBroadcaster` private → public（兼容 WorkerRef 接口）
  - `worker-service.ts`：`sanitizeEnv` 返回值加 `as Record<string, string>`
  - `GracefulShutdown.ts`：`'SHUTDOWN'` → `'SYSTEM'`（不在 Component 类型里）

**待处理（下次会话继续）**

- [ ] 集成测试验收剩余项（8.5）— Viewer UI、build-sync.py
- [ ] 构建发布流程文档（8.6）
