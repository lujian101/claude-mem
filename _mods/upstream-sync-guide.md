# 上游同步操作手册

> 从 thedotmack/claude-mem 合并更新到 lujian101/claude-mem

---

## 快速流程

```bash
# 1. 拉取上游最新
git fetch upstream

# 2. 查看更新内容
git log HEAD..upstream/main --oneline

# 3. 检查冲突热区
git diff HEAD..upstream/main -- src/services/worker/OpenRouterAgent.ts src/shared/SettingsDefaultsManager.ts

# 4. 合并（应能 fast-forward）
git merge upstream/main

# 5. 如有冲突，参考下方冲突解决指引

# 6. 重新构建
npm run build

# 7. 同步到本地 marketplace
npm run build-and-sync

# 8. 验证 worker 运行
curl http://localhost:37777/health

# 9. 推送到 fork
git push origin main
```

## 冲突解决指引

### OpenRouterAgent.ts 冲突

本地改动：新增 `baseUrl` 参数传递和智能头部逻辑
解决策略：保留上游新功能 + 重新应用 `baseUrl` patch

关键保留项：
- `getOpenRouterConfig()` 返回值增加 `baseUrl`
- `queryOpenRouterMultiTurn()` 参数增加 `baseUrl`
- 智能头部判断逻辑（`isOpenRouterOfficial`）
- API URL 使用 `apiUrl` 而非硬编码 `OPENROUTER_API_URL`

### SettingsDefaultsManager.ts 冲突

本地改动：新增 `CLAUDE_MEM_OPENROUTER_BASE_URL` 配置项
解决策略：保留新增行，其余采用上游版本

### UI 文件冲突

本地改动：新增 Base URL 输入框
解决策略：保留新增的 FormField 组件

## 合并后验证清单

- [ ] Worker 启动正常：`curl http://localhost:37777/health`
- [ ] Viewer UI 可访问：http://localhost:37777
- [ ] OpenRouter 设置中 Base URL 字段可见
- [ ] 用国内 LLM 端点测试一次摘要生成
- [ ] hooks.json 中无 `lujian101` 残留引用
