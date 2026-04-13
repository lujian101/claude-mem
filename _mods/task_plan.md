# claude-mem Fork 管理计划

> 目标：建立系统化的 fork 维护体系，降低上游合并成本，实现一键同步发布

---

## 阶段一：研究 Marketplace 机制与最小修改方案

- [ ] 1.1 分析 Claude Code 插件安装流程（/plugin 命令如何解析 marketplace.json）
- [ ] 1.2 确认 `name` vs `homepage` 的精确作用
  - 假设：`name` = 本地目录名，`homepage` = 下载源
  - 验证：改为 `name: "thedotmack"` + `homepage: "https://github.com/lujian101/claude-mem"` 是否可行
- [ ] 1.3 验证 cache 路径是否也跟随 name 字段
- [ ] 1.4 制定迁移方案：`~/.claude/plugins/marketplaces/lujian101/` → `thedotmack/`
- [ ] 1.5 确认 hooks.json 中 `CLAUDE_PLUGIN_ROOT` 环境变量是否已经覆盖路径问题

**决策点**：是否回退品牌替换，采用最小修改方案

## 阶段二：创建本地文档目录 & 整理现有文件

- [ ] 2.1 创建 `local/` 目录，用于存放所有 fork 自有文档
- [ ] 2.2 迁移 `OPENROUTER_COMPAT_PATCH.md` → `local/`
- [ ] 2.3 迁移 `MANUAL_WORKER_MANAGEMENT.md` → `local/`
- [ ] 2.4 评估现有 .bat 脚本问题，决定是重写还是废弃
- [ ] 2.5 添加 `.gitignore` 条目（如需要）
- [ ] 2.6 确保根目录文件结构与上游保持一致

**目录结构**：
```
local/
├── patches/                  # 本地修改记录
│   ├── openrouter-compat.md  # OpenRouter 兼容修改详情
│   └── worker-management.md  # Worker 手动管理修改详情
├── guides/                   # 操作指南
│   ├── upstream-sync.md      # 上游同步操作手册
│   ├── build-and-release.md  # 构建发布流程
│   └── conflict-hotzone.md   # 冲突热区地图
├── notes/                    # 技术发现和踩坑
│   ├── marketplace-mechanism.md  # 插件机制解析
│   ├── windows-adaptation.md     # Windows 适配要点
│   └── gotchas.md                # 通用踩坑记录
└── README.md                 # 本地文档索引
```

## 阶段三：编写修改记录（patches/）

- [ ] 3.1 OpenRouter 兼容修改详细记录
  - 修改了哪些文件，每个文件的具体改动
  - 新增配置项清单和默认值
  - 智能头部处理逻辑说明
  - 国内 LLM 端点配置模板
- [ ] 3.2 Worker 手动管理修改记录
  - 为什么禁用自动启动（多实例问题）
  - hooks.json 的具体变更对比
  - .bat 脚本的预期行为
- [ ] 3.3 配置项速查表
  - 所有本地新增配置项、类型、默认值、说明
- [ ] 3.4 冲突热区地图
  - 标记每次合并时容易冲突的文件及原因

## 阶段四：编写技术发现（notes/）

- [ ] 4.1 Claude Code 插件机制解析
  - marketplace.json 各字段作用
  - 插件安装目录结构
  - hooks.json 的 CLAUDE_PLUGIN_ROOT 机制
  - cache 目录的版本管理机制
- [ ] 4.2 Windows 适配要点
  - 上游 hooks 的 nvm/PATH 逻辑在 Windows 上的问题
  - rsync 在 Windows 上的可用性
  - 进程管理差异
- [ ] 4.3 通用踩坑记录
  - 多实例 worker 进程冲突
  - 国内 LLM 端点兼容性问题

## 阶段五：编写操作手册（guides/）

- [ ] 5.1 上游同步操作手册
  - Step 1: 拉取上游更新 `git fetch upstream`
  - Step 2: 分析更新内容 `git log HEAD..upstream/main --oneline`
  - Step 3: 识别冲突热区 `git diff HEAD..upstream/main -- <hotzone-files>`
  - Step 4: 合并 `git merge upstream/main`
  - Step 5: 解决冲突（按冲突热区地图指引）
  - Step 6: 重新应用本地 patch（如需要）
  - Step 7: 验证
- [ ] 5.2 构建发布流程
  - `npm run build-and-sync` 全流程说明
  - 版本号管理
  - Worker 重启验证
- [ ] 5.3 冲突热区地图
  - 高风险文件清单及合并策略
  - 低风险文件（可自动合并）

## 阶段六：品牌替换回退（取决于阶段一结论）

- [ ] 6.1 创建新分支 `refactor/minimal-fork`
- [ ] 6.2 回退所有 `thedotmack → lujian101` 的纯品牌替换
- [ ] 6.3 只保留必要修改：
  - `marketplace.json`: 仅改 homepage
  - `plugin.json`: 仅改 repository
  - OpenRouter 兼容代码
  - Worker 管理调整
- [ ] 6.4 迁移本地安装目录
- [ ] 6.5 全量测试验证

## 阶段七：创建管理技能

- [ ] 7.1 创建 `local/skills/` 目录存放自定义 skill
- [ ] 7.2 上游同步 skill（`/sync-upstream`）
  - 自动 fetch、分析变更、报告冲突风险
- [ ] 7.3 本地构建发布 skill（`/build-release`）
  - 编译、同步到 marketplace、重启 worker、验证
- [ ] 7.4 变更分析 skill（`/analyze-upstream`）
  - 对比上游差异，生成变更报告

---

## 当前阶段

**阶段一** - 研究 Marketplace 机制

## 关键决策记录

| 日期 | 决策 | 原因 |
|------|------|------|
| 2026-04-13 | 启动 fork 管理体系规划 | 上游更新频繁，手动合并成本高 |
