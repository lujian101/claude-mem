# claude-mem Fork 管理计划

> 目标：建立系统化的 fork 维护体系，降低上游合并成本，实现一键同步发布

---

## 阶段一：研究 Marketplace 机制与最小修改方案 ✅ 已完成

- [x] 1.1 分析 Claude Code 插件安装流程
- [x] 1.2 确认 marketplace.json 各字段作用
  - **结论**：`name`/`homepage`/`owner` 全是纯展示，不影响安装
  - **Marketplace source** = 用户 `add` 时指定的仓库地址
  - **Plugin source** = `source` 字段（`"./plugin"` 仓库内相对路径）
- [x] 1.3 验证 CLAUDE_PLUGIN_ROOT 环境变量 → 运行时始终设置，fallback 路径几乎不触发
- [x] 1.4 结论：marketplace.json 与上游零差异即可

**关键决策**：品牌替换完全不必要，回退所有 lujian101 → thedotmack

## 阶段二：创建本地文档目录 & 整理现有文件 ✅ 已完成

- [x] 2.1 创建 `_mods/` 目录（改为 `_mods/` 非 `local/`，避免与上游冲突）
- [x] 2.2 迁移 `OPENROUTER_COMPAT_PATCH.md` → `_mods/`
- [x] 2.3 迁移 `MANUAL_WORKER_MANAGEMENT.md` → `_mods/`
- [x] 2.4 迁移 .bat 脚本 → `_mods/`（有问题待重写）
- [x] 2.5 根目录文件结构与上游保持一致

## 阶段三：编写修改记录 ✅ 基本完成

- [x] 3.1 `_mods/README.md` — 修改点总览、配置示例、冲突热区
- [x] 3.2 `_mods/OPENROUTER_COMPAT_PATCH.md` — 原有详细记录（已迁移）
- [ ] 3.3 配置项完整速查表（当前分散在 README.md 中）

## 阶段四：编写技术发现 ✅ 基本完成

- [x] 4.1 `_mods/marketplace-mechanism.md` — 插件安装流程、字段解析、Marketplace vs Plugin source
- [x] 4.2 `_mods/findings.md` — 修改分类、上游对比分析
- [ ] 4.3 Windows 适配要点（待补充）
- [ ] 4.4 通用踩坑记录（待补充）

## 阶段五：编写操作手册 ✅ 基本完成

- [x] 5.1 `_mods/upstream-sync-guide.md` — 上游同步流程、冲突解决指引、验证清单
- [ ] 5.2 构建发布流程详细说明
- [ ] 5.3 冲突热区地图（当前在 README.md 中有简化版）

## 阶段六：品牌替换回退 & 上游合并 ✅ 已完成

- [x] 6.1 创建分支 `refactor/minimal-fork`
- [x] 6.2 回退所有 lujian101 → thedotmack（30+ 源文件 + 编译产物重建）
- [x] 6.3 marketplace.json 与上游完全一致（零修改）
- [x] 6.4 合并 upstream/main（162 commits，6 个冲突已解决）
- [x] 6.5 编译成功，推送到 origin/main

## 阶段七：Worker 稳定性修复 & 手动管理模式 ✅ 已完成

- [x] 7.1 Worker 启动机制分析
  - [x] 完整梳理 hook → ensureWorkerRunning → worker spawner 链路
  - [x] 定位卡死根因：Bun/Windows fetch() 阻塞事件循环，fetchWithTimeout 的 setTimeout 无法触发
- [x] 7.2 Hook 安全网（进程级超时）
  - [x] hook-command.ts 加 safety timer + Windows Toast 通知
  - [x] 超时时间可配置（CLAUDE_MEM_HOOK_TOTAL_TIMEOUT_MS，默认 30s）
- [x] 7.3 手动 Worker 管理模式
  - [x] SettingsDefaultsManager 新增 CLAUDE_MEM_WORKER_AUTO_START（默认 true）
  - [x] worker-spawner.ts ensureWorkerStarted() 检查配置，false 时跳过 spawn
  - [x] worker-utils.ts 在手动模式 + worker 不可达时弹 Toast 提醒（5 分钟冷却）
- [x] 7.4 网页端 Base URL 修复
  - [x] SettingsRoutes.ts settingKeys 加 CLAUDE_MEM_OPENROUTER_BASE_URL
  - [x] useSettings.ts 加载时读取该字段
- [x] 7.5 管理脚本
  - [x] 创建 worker-start.bat / worker-stop.bat / worker-status.bat（~/.claude-mem/）
  - [x] 修复：改用 worker-cli.js 而非 worker-service.cjs（前者不走 HTTP 不卡死）
- [x] 7.6 settings.json 更新
  - [x] 已添加 WORKER_AUTO_START=false, HOOK_TOTAL_TIMEOUT_MS=10000

## 阶段八：Worker 修复 & 工具链完善 🔄 进行中

- [x] 8.1 Worker 启动失败修复 — AUTO_START 守卫拦截
  - 根因：`WORKER_AUTO_START=false` 拦截了 CLI `start` 命令（只应拦 hook 自动拉起）
  - 修复：`ensureWorkerStarted` 加 `force` 参数，CLI `start` 传 `force=true`
  - commit: 7ae83401

- [x] 8.2 Worker 启动失败修复 — 僵尸端口拦截
  - 新增 `findPortHolderPid()`（netstat）+ `cleanupZombiePort()`（杀持有者+等待释放）
  - worker-spawner 集成 Windows 僵尸端口守卫
  - commit: 380668f6

- [x] 8.3 HealthMonitor 超时修复
  - 3 个裸 fetch() 全部加 `AbortSignal.timeout(3000)`
  - httpRequestToWorker / isPortInUse / httpShutdown
  - commit: 380668f6

- [x] 8.4 Windows 同步脚本 & 工具链
  - [x] `_mods/check-sync.py` — 插件文件 diff/sync（MD5 + 时间戳 + 增量同步）
  - [x] `_mods/build-sync.py` — 交互式 build-diff-sync 三步流程
  - [x] `_mods/build-sync.bat` — Windows 版交互式流程
  - [x] `_mods/worker-scripts/` — worker-manage.py + 三个 bat 入口（自动版本检测）
  - [x] `_mods/sync-worker-scripts.bat` — 一键同步 worker 脚本到 ~/.claude-mem/
  - [x] `.vscode/launch.json` — Python 调试配置

- [x] 8.7 Managed 模式 Shutdown 修复（新发现的关键 bug）
  - 根因：managed 路径跳过 graceful cleanup，wrapper taskkill 留僵尸端口
  - Chroma 子进程树杀不干净，继承 socket handle → 端口不释放
  - 修复：统一路径，始终先 `performGracefulShutdown()` 再退出
  - commit: 43fe99d7

- [x] 8.8 Auto-Start 守卫修复（新发现的关键 bug）
  - 根因：`SettingsDefaultsManager.get()` 不读 settings.json，只查 env+默认值
  - 修复：改用 `loadFromFile(USER_SETTINGS_PATH)` 走完整优先级链
  - commit: 676732c3

- [x] 8.9 Worker 启动/关闭验证（3 轮 start/stop/restart 循环）
  - managed 模式 PID 检查跳过（F15 修复）验证通过
  - MANUAL_START 绕过 disabled guard（F16 修复）验证通过
  - graceful shutdown 端口干净释放，3 轮零失败

- [x] 8.10 worker-manage.py env 传递修复（F18）
  - 根因：`subprocess.run()` 未传 `env=env`，MANUAL_START 丢失
  - 修复：添加 `env=env` + `os` import，worker-start.bat 验证通过

- [x] 8.11 TypeScript 编译错误修复
  - `'TRANSCRIPT'` 加入 Component 联合类型（logger.ts）
  - `ensureWorkerStarted` → `ensureWorkerStartedShared`（worker-service.ts）
  - `sseBroadcaster` private → public（兼容 WorkerRef 接口）
  - `sanitizeEnv` 加 `as Record<string, string>` 类型断言
  - GracefulShutdown.ts `'SHUTDOWN'` → `'SYSTEM'`

- [ ] 8.5 集成测试验收（部分完成）
  - [x] Worker 手动启动/停止/状态查询完整流程（3 轮循环通过）
  - [x] **新的 graceful shutdown 是否干净释放端口** — ✅
  - [x] **WORKER_AUTO_START=false 是否真正阻止自动启动** — ✅
  - [ ] Viewer UI Base URL 显示是否正确
  - [ ] check-sync.py / build-sync.py 功能完整性

- [ ] 8.6 构建发布流程文档
  - [ ] bump version → build → sync → push 完整流程
  - [ ] 版本号与 marketplace 更新机制的关系

---

## 当前状态

**分支**：`main`
**版本**：v12.1.0（与上游同步）
**与上游差异**：10 个文件 + `_mods/` 目录 + `.vscode/`
**本次会话**：修复 worker 路径不匹配（F19），重写 worker-manage SKILL.md，验证 hook 超时行为（F20）
**编译产物状态**：项目/cache/marketplace 三处一致
**配置状态**：WORKER_AUTO_START=false, HOOK_TOTAL_TIMEOUT_MS=10000, enabledPlugins=false
**端口状态**：37777 空闲（手动管理模式）
**下一步**：集成测试验收剩余项（8.5）→ 构建发布流程文档（8.6）

## 关键决策记录

| 日期 | 决策 | 原因 |
|------|------|------|
| 2026-04-13 | 回退全部品牌替换 | 官方文档确认 marketplace.json 不影响安装源 |
| 2026-04-13 | marketplace.json 零修改 | Marketplace source 由 add 命令决定，不在 json 里 |
| 2026-04-13 | hooks.json 采用上游版本 | 上游新增了健康检查、file-context hook，先用着看 |
| 2026-04-13 | 本地文档放入 `_mods/` | 下划线前缀避免与上游未来新增目录冲突 |
| 2026-04-13 | 版本号不变 marketplace 不拉取新文件 | 需 bump version 或手动同步构建产物到安装目录 |
| 2026-04-15 | 用 safety timer 而非修 fetchWithTimeout | Bun/Windows 下 fetch 阻塞事件循环，setTimeout 在 fetch 之前注册可兜底 |
| 2026-04-15 | 手动管理模式而非引用计数 | Hook 无状态，引用计数难做对；手动管理简单可靠 |
| 2026-04-15 | 管理脚本用 worker-cli.js | worker-service.cjs status 用裸 fetch 卡死，worker-cli.js 用 process.kill 不卡 |
| 2026-04-15 | Windows Toast 通知而非日志标记 | 用户要求实时感知，Toast 最直观 |
| 2026-04-15 | CLI start 用 force 参数绕过 auto-start | AUTO_START 本意是拦 hook 自动拉起，不该拦手动 CLI |
| 2026-04-15 | 工具链用 Python 而非 bat | 跨平台、可调试、自动版本检测，bat 只做入口 |
