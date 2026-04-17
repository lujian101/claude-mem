# 上游同步操作手册

> 从 thedotmack/claude-mem 合并更新到 lujian101/claude-mem

---

## 快速流程（使用 merge-guard 脚本）

```bash
# 1. 快照当前状态（创建 tag + 文件哈希清单）
python _mods/upstream-merge-guard.py snapshot

# 2. 预览上游变更
python _mods/upstream-merge-guard.py preview

# 3. 执行合并
python _mods/upstream-merge-guard.py merge

# 4. 校验本地修改是否完整（核心步骤！）
python _mods/upstream-merge-guard.py verify

# 5. 如有问题，查看详细 diff
python _mods/upstream-merge-guard.py diff

# 6. 确认无误后，构建 + 同步
npm run build-and-sync

# 7. 验证 worker
curl http://localhost:37777/health

# 8. 推送到 fork
git push origin main

# 9. 清理快照（可选）
rm _mods/.merge-snapshot.json
git tag -d pre-merge-*
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
