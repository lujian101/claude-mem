# _mods/ — 本地 Fork 修改汇总

> 所有属于 lujian101 fork 的自有文档集中存放于此。仓库根目录结构与上游保持一致。

---

## 修改点一览

### Patch 1: OpenRouter 国内 LLM 兼容

**文件** | **改动摘要**
---|---
`src/services/worker/OpenRouterAgent.ts` | 新增 `baseUrl` 配置，智能判断是否发送 OpenRouter 特有头部（`HTTP-Referer`/`X-Title`），仅官方端点才发送
`src/shared/SettingsDefaultsManager.ts` | 新增 `CLAUDE_MEM_OPENROUTER_BASE_URL` 配置项，默认值 `https://openrouter.ai/api/v1/chat/completions`
`src/ui/viewer/components/ContextSettingsModal.tsx` | UI 增加 Base URL 输入框
`src/ui/viewer/constants/settings.ts` | 新增 `CLAUDE_MEM_OPENROUTER_BASE_URL` 默认值
`src/ui/viewer/types.ts` | Settings 类型新增 `CLAUDE_MEM_OPENROUTER_BASE_URL`

**配置示例（智谱 AI）**：
```json
{
  "CLAUDE_MEM_PROVIDER": "openrouter",
  "CLAUDE_MEM_OPENROUTER_API_KEY": "your-key",
  "CLAUDE_MEM_OPENROUTER_MODEL": "glm-4-flash",
  "CLAUDE_MEM_OPENROUTER_BASE_URL": "https://open.bigmodel.cn/api/paas/v4/chat/completions"
}
```

**国内端点参考**：

| 提供商 | 端点 | 免费模型 |
|--------|------|----------|
| 智谱 AI | `https://open.bigmodel.cn/api/paas/v4/chat/completions` | `glm-4-flash` |
| DeepSeek | `https://api.deepseek.com/v1/chat/completions` | `deepseek-chat` |
| 月之暗面 | `https://api.moonshot.cn/v1/chat/completions` | - |
| 阿里通义 | `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions` | `qwen-turbo-free` |

### Patch 2: marketplace.json 零修改

**文件**: `.claude-plugin/marketplace.json` — **与上游完全一致，无需任何改动**

**原理**: Claude Code 插件安装源由两层独立控制，都不在 `marketplace.json` 里：
1. **Marketplace source**（市场源）— 用户执行 `/plugin marketplace add lujian101/claude-mem` 时指定的仓库地址
2. **Plugin source**（插件源）— `source` 字段（当前为 `"./plugin"`，仓库内相对路径）

`marketplace.json` 里的 `name`、`homepage` 等字段都是纯展示用途，不影响下载和安装行为。

详见 [marketplace-mechanism.md](marketplace-mechanism.md)

---

## 合并冲突热区

合并上游时，**只有以下文件可能冲突**（因为有本地功能修改）：

| 文件 | 风险 | 原因 |
|------|------|------|
| `src/services/worker/OpenRouterAgent.ts` | 中 | 本地有 baseUrl 功能改动 |
| `src/shared/SettingsDefaultsManager.ts` | 低 | 本地有新增配置项 |
| `src/ui/viewer/` 下 3 个文件 | 低 | 本地有 UI 改动 |

其余所有文件应能 **fast-forward** 合并。

---

## 文件索引

| 文件 | 内容 |
|------|------|
| `README.md` | 本文件 — 修改点总览 |
| `marketplace-mechanism.md` | Claude Code 插件市场机制解析 |
| `upstream-sync-guide.md` | 上游同步操作手册 |
| `OPENROUTER_COMPAT_PATCH.md` | OpenRouter 兼容修改详细记录（迁移自根目录） |
| `MANUAL_WORKER_MANAGEMENT.md` | Worker 手动管理记录（迁移自根目录） |
