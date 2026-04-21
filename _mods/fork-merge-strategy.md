# Fork 上游合并策略

> 记录我们与上游 thedotmack/claude-mem 的代码分歧点、合并经验、以及下次合并前的重构计划

## 上游信息

- 上游仓库: https://github.com/thedotmack/claude-mem
- 最近一次合并: 2026-04-20, 上游版本 v12.3.2
- 合并提交: fbdbaa6c

---

## 我们的代码分歧点

### 1. OpenRouter baseUrl 自定义端点支持

- **文件**: `src/services/worker/OpenRouterAgent.ts`
- **目的**: 支持自定义 OpenRouter 端点（国内模型代理），不硬编码 `openrouter.ai`
- **当前做法**: `baseUrl` 在 `getOpenRouterConfig()` 中读取，然后作为参数穿过整条调用链：`startSession()` → `processOneMessage()` → `processObservationMessage()` / `processSummaryMessage()` → `queryOpenRouterMultiTurn()`
- **合并痛点**: 整条调用链每个函数签名都要加 `baseUrl` 参数，上游一重构（拆出 helper 方法）就全断了，这次合并改了 5 个函数签名
- **下次合并前重构方案**: 去掉参数传递。让 `queryOpenRouterMultiTurn()` 内部直接从 `SettingsDefaultsManager` 读取 `CLAUDE_MEM_OPENROUTER_BASE_URL`，它内部已经在用同样的方式读其他配置了。函数签名零改动 = 合并零冲突

### 2. Hook 安全网（进程级超时 + Windows Toast 通知）

- **文件**: `src/cli/hook-command.ts`
- **目的**: 防止 hook 在 Bun/Windows 上无限挂起；超时时弹出 Windows 气泡通知提醒用户
- **当前做法**: 直接写在 `hookCommand()` 函数体里（safetyTimer 设置 + PowerShell toast 命令）
- **合并痛点**: 位于 `hookCommand` 函数体内部，上游持续重构这个函数
- **下次合并前重构方案**: 把 toast 逻辑抽到 `src/utils/windows-toast.ts`。`hook-command.ts` 只加一行 `import` + 一行函数调用。冲突面缩小到一行代码

### 3. Worker-manage 管理技能

- **文件**: `plugin/skills/worker-manage/SKILL.md`
- **目的**: 会话内管理 worker（start/stop/restart/status/logs）
- **合并痛点**: 无 — 已经是独立文件，和上游代码没有重叠

### 4. CLAUDE_MEM_HOOK_TOTAL_TIMEOUT_MS 配置项

- **文件**: `src/cli/hook-command.ts`, `src/shared/SettingsDefaultsManager.ts`
- **目的**: 可配置的进程级 hook 超时时间（默认 30 秒，范围 5-120 秒）
- **合并痛点**: 通过 `SettingsDefaultsManager` 读取，该文件自动合并无冲突，风险低

---

## 下次合并前 Checklist

1. `git fetch upstream && git log --oneline upstream/main ^main` 查看上游新提交
2. 先执行本文档中的重构计划（baseUrl 内部读取、toast 抽离）
3. 用 `_mods/upstream-merge-guard.py preview` 预览冲突
4. 解决冲突时优先采用上游重构后的结构，再叠加我们的改动
5. 冲突解决后 `npm run build` 重新生成编译产物
6. 验证我们的自定义功能是否正常（worker-manage、baseUrl、toast 通知）

---

## Fork 定制代码设计原则

1. **配置就近读取** — 不把 settings 配置作为参数穿过调用链，谁用谁自己读
2. **独立文件/模块** — 自定义代码放独立文件，通过 import 引入
3. **最小侵入** — 在上游文件里只加一行 import + 一行调用，不再多改
4. **记录每一个分歧** — 新增自定义功能时，更新本文档

---

## 合并经验教训（2026-04-20）

- 上游频繁重构（301 反模式清理一次改了 90 个文件），编译产物（.cjs/.js）不需要手动解决冲突，build 就行
- 真正的源码冲突不多，这次只有 `.gitignore`、`hook-command.ts`、`OpenRouterAgent.ts` 三个
- 上游删除了大量自动生成的 CLAUDE.md 文件，这些不影响功能
- `_mods/` 目录下的文件上游全删了（他们清理了贡献工具），我们本地加的文件不受影响，但下次要注意
