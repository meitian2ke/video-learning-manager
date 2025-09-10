# 部署指南

## 🚀 CI/CD自动部署 (推荐)

### 1. 设置GitHub仓库

```bash
# 1. 创建GitHub仓库
# 访问 https://github.com/new
# 仓库名: video-learning-manager

# 2. 推送代码
git init
git add .
git commit -m "feat: 初始化视频学习管理器项目"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/video-learning-manager.git
git push -u origin main
```

### 2. 在Debian服务器设置Self-hosted Runner

```bash
# 在服务器上运行
cd /home/YOUR_USER
wget https://raw.githubusercontent.com/YOUR_USERNAME/video-learning-manager/main/scripts/setup-github-runner.sh
chmod +x setup-github-runner.sh
./setup-github-runner.sh
```

### 3. 配置GitHub Secrets

在GitHub仓库设置中添加以下Secrets：
- `GITHUB_TOKEN`: 自动生成，用于容器仓库访问
- `SLACK_WEBHOOK_URL`: (可选) Slack通知webhook

路径：`仓库设置 → Secrets and variables → Actions → New repository secret`

### 4. 触发自动部署

```bash
# 推送到main分支即可触发自动部署
git push origin main
```

## 🛠️ 手动部署

### 1. 准备服务器环境

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker

# 安装Docker Compose
sudo apt install docker-compose-plugin -y

# 验证安装
docker --version
docker compose version
```

### 2. 部署应用

```bash
# 克隆项目
git clone https://github.com/YOUR_USERNAME/video-learning-manager.git
cd video-learning-manager

# 运行部署脚本
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

### 3. 配置环境变量

```bash
# 编辑生产环境配置
cp .env.production /opt/video-learning-manager/.env
nano /opt/video-learning-manager/.env

# 重要：修改以下配置
# - SECRET_KEY: 设置强密码
# - GITHUB_REPOSITORY: 你的仓库路径
# - SLACK_WEBHOOK_URL: (可选) 通知配置
```

## 📊 监控和维护

### 日常监控

```bash
# 运行监控脚本
./scripts/monitor.sh

# 查看服务状态
docker ps

# 查看实时日志
docker-compose -f /opt/video-learning-manager/docker-compose.prod.yml logs -f

# 查看特定服务日志
docker logs video-manager-backend -f
```

### 常用维护命令

```bash
# 重启所有服务
docker-compose -f /opt/video-learning-manager/docker-compose.prod.yml restart

# 重启特定服务
docker-compose -f /opt/video-learning-manager/docker-compose.prod.yml restart backend

# 更新镜像
docker-compose -f /opt/video-learning-manager/docker-compose.prod.yml pull
docker-compose -f /opt/video-learning-manager/docker-compose.prod.yml up -d

# 清理无用镜像
docker system prune -f

# 备份数据
cp -r /opt/video-learning-manager/data /opt/backups/video-learning-manager/backup-$(date +%Y%m%d)
```

## 🔧 故障排除

### 服务无法启动

```bash
# 检查端口占用
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep :8000

# 检查磁盘空间
df -h

# 检查内存使用
free -h

# 查看详细错误日志
docker-compose -f /opt/video-learning-manager/docker-compose.prod.yml logs
```

### 数据库问题

```bash
# 进入后端容器
docker exec -it video-manager-backend bash

# 检查数据库文件
ls -la /app/data/

# 重新初始化数据库（谨慎使用）
rm /app/data/video_learning.db
# 重启服务会自动重新创建
```

### 网络问题

```bash
# 检查Docker网络
docker network ls
docker network inspect video-manager-network

# 重新创建网络
docker-compose -f /opt/video-learning-manager/docker-compose.prod.yml down
docker network prune
docker-compose -f /opt/video-learning-manager/docker-compose.prod.yml up -d
```

## 🔄 更新流程

### 自动更新 (推荐)
1. 修改代码并推送到GitHub
2. GitHub Actions自动构建和部署
3. 监控部署状态

### 手动更新
```bash
cd video-learning-manager
git pull origin main
./scripts/deploy.sh
```

## 📈 性能优化

### 数据库优化
```bash
# 定期清理旧数据
docker exec -it video-manager-backend python -c "
from app.core.database import SessionLocal
from app.core.database import Video
from datetime import datetime, timedelta

db = SessionLocal()
old_date = datetime.now() - timedelta(days=90)
old_videos = db.query(Video).filter(Video.created_at < old_date, Video.status == 'failed').all()
for video in old_videos:
    db.delete(video)
db.commit()
print(f'清理了 {len(old_videos)} 个失败的视频记录')
"
```

### 文件存储优化
```bash
# 清理临时音频文件
find /opt/video-learning-manager/audios -name "*.wav" -mtime +7 -delete

# 压缩旧视频文件
find /opt/video-learning-manager/videos -name "*.mp4" -mtime +30 -exec gzip {} \;
```

## 🔐 安全配置

### SSL证书 (可选)
```bash
# 安装certbot
sudo apt install certbot

# 申请SSL证书
sudo certbot certonly --standalone -d your-domain.com

# 配置Nginx SSL
# 编辑 /opt/video-learning-manager/nginx.conf 添加SSL配置
```

### 防火墙配置
```bash
# 配置UFW防火墙
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

## 📞 获取帮助

- 查看GitHub Issues
- 运行监控脚本诊断问题
- 检查Docker日志获取详细错误信息