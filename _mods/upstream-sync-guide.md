# 上游同步操作手册

> 从 thedotmack/claude-mem 合并更新到 lujian101/claude-mem

---

## 完整流程

### 1. 合并前：暂存本地修改

```bash
# 查看本地有哪些未提交的改动
git status

# 暂存本地修改（stash）
git stash push -m "pre-upstream-merge-stash"
```

**为什么必须 stash**：上游和本地都改了 `worker-service.ts` 等文件，不先 stash 的话 git merge 会直接报错拒绝合并。

### 2. 合并上游

```bash
git fetch upstream
git merge upstream/main --no-edit
```

### 3. 处理冲突

合并后大概率有冲突文件，分两类处理：

#### 编译产物 → 直接用上游版本

以下文件是 `npm run build` 的输出，**不需要手动合并**，直接取上游：

```bash
git checkout --theirs \
  plugin/scripts/context-generator.cjs \
  plugin/scripts/mcp-server.cjs \
  plugin/scripts/worker-service.cjs \
  plugin/ui/viewer-bundle.js
git add plugin/scripts/context-generator.cjs \
  plugin/scripts/mcp-server.cjs \
  plugin/scripts/worker-service.cjs \
  plugin/ui/viewer-bundle.js
```

**原理**：这些 `.cjs` / `.js` 是从 `src/` 编译出来的。源码合并正确后，重新 build 就会生成我们自己的版本。

#### 源码文件 → 需要手动检查

- `src/services/worker-service.ts`：git 通常能自动合并，检查一下即可
- 其他 `src/` 下的冲突：根据实际情况解决

### 4. 提交合并

```bash
git commit -m "merge: sync upstream thedotmack/claude-mem (N commits, vX.Y.Z)"
```

### 5. 恢复本地修改

```bash
git stash pop
```

如果编译产物又冲突，同样的套路：直接用上游版本覆盖。

```bash
git checkout --theirs plugin/scripts/mcp-server.cjs plugin/scripts/worker-service.cjs
git add plugin/scripts/mcp-server.cjs plugin/scripts/worker-service.cjs
```

### 6. 重新编译

```bash
npm run build
```

### 7. 同步到 marketplace

Windows 没有 rsync，`npm run build-and-sync` 会失败。手动同步：

```bash
MARKETPLACE="$HOME/.claude/plugins/marketplaces/thedotmack"
cp -r plugin/scripts/* "$MARKETPLACE/plugin/scripts/"
cp -r plugin/ui/* "$MARKETPLACE/plugin/ui/"
cp -r plugin/skills/* "$MARKETPLACE/plugin/skills/"
cp -r plugin/hooks/* "$MARKETPLACE/plugin/hooks/"
cp plugin/package.json "$MARKETPLACE/plugin/"
cp plugin/.mcp.json "$MARKETPLACE/plugin/"
cp package.json "$MARKETPLACE/"
cp .claude-plugin/plugin.json "$MARKETPLACE/.claude-plugin/"
```

### 8. 验证

```bash
curl http://localhost:37777/health
```

### 9. 提交本地补丁 + 推送

```bash
git add .
git commit -m "fix: apply local patches on top of upstream vX.Y.Z"
git push origin main
```

---

## 关键经验总结

| 问题 | 解决方案 |
|------|---------|
| 本地有未提交修改导致 merge 失败 | 先 `git stash`，合并后再 `git stash pop` |
| 编译产物冲突（`.cjs` / `viewer-bundle.js`） | `git checkout --theirs`，不需要手动合并 |
| `npm run build-and-sync` 在 Windows 失败 | rsync 不可用，手动 cp 到 marketplace 目录 |
| stash pop 又导致编译产物冲突 | 同样 `--theirs` 覆盖，反正 build 会重新生成 |
| 上游删除了 `_mods/` 目录 | 不影响，`_mods/` 是本地文件且在 stash 里 |

## 注意事项

- 编译产物**永远不要手动合并**，源码合并后 build 一次就搞定
- 每次同步前确认 `upstream` remote 存在：`git remote -v`
- 同步完成后验证 worker 健康状态再推送
