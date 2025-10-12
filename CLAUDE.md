# Claude Code 项目记忆文件

## 重要架构信息

### 开发与部署环境分离
- **开发环境**: macOS，仅用于代码开发，Claude Code 在此运行
- **生产环境**: Debian 服务器，实际运行 Docker 容器
- **注意**: 在 macOS 上修改配置文件没有实际效果，需要在 Debian 服务器上操作

### 端口冲突问题
- 服务器上已运行 `ai-video-transcriber` 项目，功能相似
- Redis 默认端口 6379 被占用，需要修改为其他端口（如 6380）
- 主应用端口 8000 和前端端口 3000 无冲突，不需要修改

### 部署流程
1. 在 macOS 开发环境推送代码: `git push origin main`
2. 在 Debian 服务器拉取更新: `git pull --force origin main`
3. 重启服务: `./run.sh restart`

## 常用命令

### 服务器端操作
```bash
# 进入项目目录
cd ~/deploy/video-learning-manager

# 服务管理
./run.sh start      # 启动服务
./run.sh stop       # 停止服务  
./run.sh restart    # 重启服务
./run.sh update     # 更新代码并重启
./run.sh status     # 查看状态
./run.sh logs       # 查看日志

# 强制更新代码
git fetch origin
git reset --hard origin/main
```

## 注意事项
- Docker 容器运行在 Debian 服务器，不在 macOS 开发机
- 配置文件修改需要在服务器端进行
- 端口冲突需要在服务器端的 docker-compose 文件中解决