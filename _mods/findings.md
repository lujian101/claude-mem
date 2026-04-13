# 研究发现

> claude-mem fork 管理相关技术发现

---

## F1: Marketplace 机制分析（已通过官方文档确认）

### 核心结论：品牌替换完全不必要

根据 Claude Code 官方文档 [Plugin Marketplaces](https://code.claude.com/docs/en/plugin-marketplaces)：

1. **插件下载源不是 `homepage` 字段**，而是用户添加 marketplace 时指定的仓库地址：
   - `/plugin marketplace add lujian101/claude-mem` → 从 lujian101 仓库克隆
   - 与 marketplace.json 中的 `name` 或 `homepage` 无关！

2. **`name` 字段只是标识符**（kebab-case），用于显示和本地引用（如 `plugin install xxx@marketplace-name`），不影响下载源。

3. **`source` 字段决定插件位置**：
   - `"source": "./plugin"` = 仓库内的相对路径（当前方案）
   - 也可以指向外部 GitHub repo、git URL、npm 包等

4. **`CLAUDE_PLUGIN_ROOT` 在运行时总是设置的**：
   > "use this variable in hooks and MCP server configs to reference files within the plugin's installation directory. This is necessary because plugins are copied to a cache location when installed."
   - hooks.json 中的硬编码 fallback 路径几乎不会触发

5. **`CLAUDE_PLUGIN_DATA`** 用于需要跨版本持久化的数据。

### marketplace.json 各字段真实作用

```json
{
  "name": "thedotmack",         // 仅标识符，显示用，不影响功能
  "owner": { "name": "..." },   // 显示用
  "metadata": {
    "description": "...",        // 显示用
    "homepage": "https://..."   // 显示用，不是下载源！
  },
  "plugins": [{
    "name": "claude-mem",
    "source": "./plugin",        // 仓库内相对路径，这才是真正的插件位置
    "version": "10.6.3"
  }]
}
```

### 实际下载流程

```
用户执行: /plugin marketplace add lujian101/claude-mem
    ↓
Claude Code: git clone https://github.com/lujian101/claude-mem
    ↓
读取: .claude-plugin/marketplace.json
    ↓
找到: plugins[0].source = "./plugin"
    ↓
复制: <repo>/plugin/ → ~/.claude/plugins/cache/<marketplace-name>/claude-mem/<version>/
    ↓
设置: CLAUDE_PLUGIN_ROOT = 上述 cache 路径
```

### 结论

**只需修改 1 个文件中的 1-2 个字段**：
- `marketplace.json` → `metadata.homepage` 改为 fork URL（纯显示用）
- 可选：`owner.name` 改为自己

**44 个文件的品牌替换全部可以回退**，不影响任何功能。

---

## F2: 本地修改分类

### 类别 A：纯品牌替换（44 个文件，可回退）

| 文件 | 改动内容 |
|------|---------|
| `.claude-plugin/marketplace.json` | name + homepage |
| `.claude-plugin/plugin.json` | repository URL |
| `plugin/hooks/hooks.json` | 所有路径 thedotmack → lujian101 |
| `scripts/sync-marketplace.cjs` | 所有路径 |
| `scripts/sync-to-marketplace.sh` | 路径 |
| `package.json` | repository/homepage/bugs URLs |
| 其他 38 个文件 | 搜索替换 thedotmack → lujian101 |

**合并影响**：每次合并上游，这些文件都会冲突（因为上游永远用 thedotmack）

### 类别 B：功能修改（需要保留）

| 文件 | 改动内容 |
|------|---------|
| `src/services/worker/OpenRouterAgent.ts` | 国内 LLM 兼容、智能头部控制 |
| `src/shared/SettingsDefaultsManager.ts` | 新增配置项 |
| `src/ui/viewer/` 相关 | UI 适配新配置 |

**合并影响**：中等风险，取决于上游是否动了这些文件

### 类别 C：行为修改（需要保留）

| 文件 | 改动内容 |
|------|---------|
| `plugin/hooks/hooks.json` | 禁用 worker 自动启动 + 简化 PATH |

**合并影响**：高风险，上游经常调整 hooks

### 类别 D：编译产物

| 文件 | 改动内容 |
|------|---------|
| `plugin/scripts/*.cjs` | 编译后包含品牌替换 |
| `plugin/ui/viewer-bundle.js` | 编译后包含品牌替换 |
| `install/public/installer.js` | 编译后 |
| `installer/dist/index.js` | 编译后 |

**合并影响**：编译产物每次 build 都会重新生成，不需要手动维护

---

## F3: 上游 hooks.json vs 本地 hooks.json 差异

### 上游版本特点
1. 设置 nvm/PATH 环境（Linux/macOS 专用）
2. Cache 目录查找 fallback
3. Worker 自动启动 + 健康检查等待
4. SessionStart 包含 3 个 hook（install + start + context）

### 本地版本特点
1. 无 PATH 设置（Windows 不需要 nvm）
2. 无 cache 查找（直接用 marketplace 路径）
3. Worker 不自动启动（手动管理）
4. SessionStart 包含 2 个 hook（install + context）

### 兼容性分析
- 上游的 nvm PATH 设置在 Windows 上会失败，但不影响功能（Windows 有自己的 node 路径）
- Cache 查找是合理的优化，本地可保留
- Worker 自动启动被禁用是用户的选择，需单独维护

---

## F4: 当前落后上游状态

- 落后 upstream/main **165 个 commit**
- 上游版本号已远超本地（本地停留在 10.6.3 的编译版本）
- 需要评估上游是否有 breaking changes

---

## F5: .bat 脚本问题

现有 .bat 脚本：
- `start-worker.bat` - 启动 worker
- `stop-worker.bat` - 停止 worker
- `restart-worker.bat` - 重启 worker
- `status-worker.bat` - 查看状态

**已知问题**：用户反馈"有问题，不好用"，具体问题待分析。后续需要重写或用 npm scripts 替代。
