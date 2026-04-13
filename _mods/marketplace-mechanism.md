# Claude Code 插件市场机制解析

> 来源：官方文档 https://code.claude.com/docs/en/plugin-marketplaces

---

## 插件下载流程

```
用户: /plugin marketplace add lujian101/claude-mem
  ↓
Claude Code: git clone https://github.com/lujian101/claude-mem
  ↓
读取: .claude-plugin/marketplace.json
  ↓
查找: plugins[0].source = "./plugin"  (仓库内相对路径)
  ↓
复制: <repo>/plugin/ → ~/.claude/plugins/cache/<marketplace-name>/claude-mem/<version>/
  ↓
运行时设置: CLAUDE_PLUGIN_ROOT = 上述 cache 路径
```

## marketplace.json 字段真相

```json
{
  "name": "thedotmack",
  // ↑ 仅显示标识符，用户安装时看到的名字
  // ↑ 不决定下载源！不影响本地路径！

  "owner": { "name": "..." },
  // ↑ 纯显示

  "metadata": {
    "homepage": "https://github.com/thedotmack/claude-mem"
    // ↑ 纯展示链接，文档/主页 URL，不影响安装
  },

  "plugins": [{
    "name": "claude-mem",
    "source": "./plugin"
    // ↑ 这才是插件在仓库内的位置
  }]
}
```

## 关键环境变量

| 变量 | 用途 |
|------|------|
| `CLAUDE_PLUGIN_ROOT` | 运行时**始终设置**，指向 cache 中的插件安装目录。hooks.json 应使用 `${CLAUDE_PLUGIN_ROOT}` 引用文件 |
| `CLAUDE_PLUGIN_DATA` | 跨版本持久化数据目录 |
| `CLAUDE_CODE_PLUGIN_SEED_DIR` | 预装插件目录（容器/CI 用） |

## plugin source 类型

| 类型 | 格式 | 说明 |
|------|------|------|
| 相对路径 | `"./plugin"` | 仓库内目录（当前方案） |
| GitHub | `{ "source": "github", "repo": "owner/repo" }` | 独立仓库 |
| Git URL | `{ "source": "url", "url": "https://..." }` | 任意 Git 服务 |
| git-subdir | `{ "source": "git-subdir", "url": "...", "path": "..." }` | 仓库子目录（稀疏克隆） |
| npm | `{ "source": "npm", "package": "@org/plugin" }` | npm 包 |

## 关键概念：Marketplace Source vs Plugin Source

文档明确区分了两个概念：

| 概念 | 控制什么 | 在哪设置 |
|------|---------|---------|
| **Marketplace source**（市场源） | 从哪拉取 `marketplace.json` 目录文件 | 用户执行 `/plugin marketplace add lujian101/claude-mem` 时指定 |
| **Plugin source**（插件源） | 从哪拉取具体插件代码 | `marketplace.json` 中每个 plugin 的 `source` 字段 |

两者独立控制，可以指向不同仓库。当前方案两者都指向同一个仓库（`lujian101/claude-mem`）。

## 结论

fork 维护者**不需要**修改 `marketplace.json` 或源码中的任何硬编码路径（`thedotmack`）。

原因：
1. Marketplace source 由 `add` 命令参数决定，不由 marketplace.json 内任何字段决定
2. Plugin source 由 `source` 字段决定（当前为 `"./plugin"`，仓库内相对路径，不需要改）
3. `CLAUDE_PLUGIN_ROOT` 在运行时始终设置，hooks.json 的 fallback 路径几乎不触发
4. `name`、`homepage`、`owner` 等字段都是纯展示

**结论：marketplace.json 与上游保持完全一致，零修改。**
