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

## 阶段七：集成测试 🔄 进行中

- [x] 7.0 前置检查
  - [x] 确认版本号不变导致 marketplace 未拉取新构建产物
  - [x] 手动同步 4 个文件到安装目录：worker-service.cjs, mcp-server.cjs, context-generator.cjs, viewer-bundle.js
  - [x] 重启电脑清理僵尸端口/进程
  - [x] 安装目录与本地项目全部一致（排除 package.json 排序差异）
- [ ] 7.1 Worker 启动测试 — hook 触发后 worker 能否正常启动并监听 37777
- [ ] 7.2 PID 验证测试 — kill bun 进程后，新 hook 能否正确检测并重启
- [ ] 7.3 端口残留场景 — 验证修复后是否还有僵尸 LISTENING 状态
- [ ] 7.4 SessionStart hook — 上下文注入是否正常
- [ ] 7.5 PostToolUse hook — 工具调用捕获是否正常
- [ ] 7.6 Viewer UI — http://localhost:37777 是否能正常访问
- [ ] 7.7 管理技能创建（/sync-upstream, /build-release, /analyze-upstream）

---

## 当前状态

**分支**：`main`（与远程同步）
**版本**：v12.1.0（与上游同步）
**与上游差异**：9 个文件（5 个 OpenRouter 源码 + 4 个编译产物）+ `_mods/` 目录
**当前任务**：集成测试（阶段七）
**前置检查**：✅ 已完成 — 构建产物已手动同步到安装目录，僵尸进程已通过重启清除

## 关键决策记录

| 日期 | 决策 | 原因 |
|------|------|------|
| 2026-04-13 | 回退全部品牌替换 | 官方文档确认 marketplace.json 不影响安装源 |
| 2026-04-13 | marketplace.json 零修改 | Marketplace source 由 add 命令决定，不在 json 里 |
| 2026-04-13 | hooks.json 采用上游版本 | 上游新增了健康检查、file-context hook，先用着看 |
| 2026-04-13 | 本地文档放入 `_mods/` | 下划线前缀避免与上游未来新增目录冲突 |
| 2026-04-13 | 版本号不变 marketplace 不拉取新文件 | 需 bump version 或手动同步构建产物到安装目录 |
