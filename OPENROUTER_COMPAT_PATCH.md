# OpenRouter 兼容国内 LLM 修改记录

## 修改日期
2026-03-03

## 修改目的
支持使用 OpenAI 兼容协议的国内 LLM 端点（如智谱 AI、DeepSeek、月之暗面等）

## 问题分析
调用智谱模型失败是因为 OpenRouter 使用了特殊的请求头（`HTTP-Referer` 和 `X-Title`），这些头部对于国内 LLM 提供商是不支持的，甚至会导致请求失败。

## 修改文件

### 1. src/shared/SettingsDefaultsManager.ts

**新增配置项：**
- `CLAUDE_MEM_OPENROUTER_API_URL`: 自定义 API URL（空值 = 使用默认 OpenRouter API）
- `CLAUDE_MEM_OPENROUTER_HEADERS_ENABLED`: 是否启用 OpenRouter 特有头部（默认: true）

**接口变更：**
```typescript
export interface SettingsDefaults {
  // ... 其他配置
  CLAUDE_MEM_OPENROUTER_API_URL: string;  // 新增
  CLAUDE_MEM_OPENROUTER_HEADERS_ENABLED: string;  // 新增
}
```

**默认值：**
```typescript
CLAUDE_MEM_OPENROUTER_API_URL: '',
CLAUDE_MEM_OPENROUTER_HEADERS_ENABLED: 'true',
```

### 2. src/services/worker/OpenRouterAgent.ts

**getOpenRouterConfig() 方法变更：**
- 返回类型新增 `apiUrl: string` 和 `enableOpenRouterHeaders: boolean`
- 添加自定义 API URL 读取逻辑
- 添加智能头部启用逻辑：只有当使用官方 OpenRouter API 时才启用特殊头部

```typescript
// 新增逻辑
const apiUrl = settings.CLAUDE_MEM_OPENROUTER_API_URL || OPENROUTER_API_URL;
const isOfficialOpenRouter = apiUrl === OPENROUTER_API_URL;
const enableOpenRouterHeaders = settings.CLAUDE_MEM_OPENROUTER_HEADERS_ENABLED !== false && isOfficialOpenRouter;
```

**queryOpenRouterMultiTurn() 方法变更：**
- 新增参数：`apiUrl: string` 和 `enableOpenRouterHeaders = true`
- 动态构建请求头，根据 `enableOpenRouterHeaders` 决定是否添加 OpenRouter 特有头部

```typescript
// 动态构建请求头
const headers: Record<string, string> = {
  'Authorization': \`Bearer \${apiKey}\`,
  'Content-Type': 'application/json',
};

if (enableOpenRouterHeaders) {
  if (siteUrl) headers['HTTP-Referer'] = siteUrl;
  if (appName) headers['X-Title'] = appName;
}
```

**调用点更新：**
- `startSession()` 方法中的 3 处 `queryOpenRouterMultiTurn()` 调用全部更新，传入新参数

## 使用示例

### 智谱 AI 配置：
```json
{
  "CLAUDE_MEM_PROVIDER": "openrouter",
  "CLAUDE_MEM_OPENROUTER_API_KEY": "your-zhipu-api-key",
  "CLAUDE_MEM_OPENROUTER_MODEL": "glm-4-flash",
  "CLAUDE_MEM_OPENROUTER_API_URL": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
  "CLAUDE_MEM_OPENROUTER_HEADERS_ENABLED": false
}
```

### DeepSeek 配置：
```json
{
  "CLAUDE_MEM_PROVIDER": "openrouter",
  "CLAUDE_MEM_OPENROUTER_API_KEY": "your-deepseek-api-key",
  "CLAUDE_MEM_OPENROUTER_MODEL": "deepseek-chat",
  "CLAUDE_MEM_OPENROUTER_API_URL": "https://api.deepseek.com/v1/chat/completions",
  "CLAUDE_MEM_OPENROUTER_HEADERS_ENABLED": false
}
```

## 技术细节

### 兼容性说明
- OpenRouter 使用标准 OpenAI 兼容协议
- 请求格式：`model`, `messages`, `temperature`, `max_tokens`
- 响应格式：`choices[0].message.content`
- 认证方式：`Authorization: Bearer {key}`

### 智能头部处理逻辑
```typescript
// 只有官方 OpenRouter API 才启用特殊头部
const isOfficialOpenRouter = apiUrl === OPENROUTER_API_URL;
const enableOpenRouterHeaders =
  settings.CLAUDE_MEM_OPENROUTER_HEADERS_ENABLED !== false &&
  isOfficialOpenRouter;
```

## 国内 LLM 端点参考

| 提供商 | 端点 | 免费模型 |
|--------|------|----------|
| 智谱 AI | `https://open.bigmodel.cn/api/paas/v4/chat/completions` | `glm-4-flash` |
| DeepSeek | `https://api.deepseek.com/v1/chat/completions` | `deepseek-chat` |
| 月之暗面 | `https://api.moonshot.cn/v1/chat/completions` | - |
| 阿里通义 | `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions` | `qwen-turbo-free` |
