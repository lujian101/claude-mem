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
