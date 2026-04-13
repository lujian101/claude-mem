# claude-mem 手动管理脚本

## 📋 脚本说明

为了解决多个 Claude Code 实例导致后台 worker 进程被杀的问题，已禁用自动启动，改为手动管理。

## 🚀 使用方法

### 快速启动
双击 `start-worker.bat` 启动后台服务

### 查看状态
双击 `status-worker.bat` 查看服务状态和端口占用

### 重启服务
双击 `restart-worker.bat` 重启服务

### 停止服务
双击 `stop-worker.bat` 停止服务

## 📝 修改内容

### 已禁用自动启动
- `plugin/hooks/hooks.json` 中删除了 SessionStart 的 `start` 命令
- 保留了 `smart-install.js` 和 `context` 命令

### 手动管理脚本
- `start-worker.bat` - 启动服务
- `stop-worker.bat` - 停止服务
- `restart-worker.bat` - 重启服务
- `status-worker.bat` - 查看状态

## ⚠️ 重要提示

1. **启动 Claude Code 前**：先运行 `start-worker.bat`
2. **多实例安全**：多个 Claude Code 实例会复用同一个后台服务
3. **关闭服务**：使用完所有 Claude Code 实例后，运行 `stop-worker.bat`
4. **僵尸端口**：如果端口被占用，运行 `restart-worker.bat` 强制重启

## 🔧 高级配置

### 修改插件路径
如果你的插件安装在其他位置，修改 `.bat` 文件中的：
```batch
set PLUGIN_ROOT=%USERPROFILE%\.claude\plugins\marketplaces\lujian101\plugin
```

### 修改端口
默认端口是 37777，如需修改，设置环境变量：
```batch
set CLAUDE_MEM_WORKER_PORT=38888
```

## 📊 故障排查

### 端口被占用
```batch
# 查找占用进程
netstat -ano | findstr :37777

# 强制结束进程
taskkill /PID <进程ID> /F
```

### 清理僵尸进程
```batch
# 停止服务
node %USERPROFILE%\.claude\plugins\marketplaces\lujian101\plugin\scripts\worker-service.cjs stop

# 等待端口释放
timeout /t 3 /nobreak

# 重新启动
start-worker.bat
```

## 🎯 最佳实践

1. **工作流程**：
   ```
   启动 worker → 打开 Claude Code → 工作 → 关闭 Claude Code → 停止 worker
   ```

2. **多实例场景**：
   ```
   启动 worker → 打开多个 Claude Code → 使用完毕 → 关闭所有实例 → 停止 worker
   ```

3. **日常使用**：
   ```
   可以一直保持 worker 运行，只在需要时重启
   ```
