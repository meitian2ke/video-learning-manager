#!/bin/bash

# 手动部署脚本 (用于测试或紧急部署)

set -e

echo "🚀 开始部署视频学习管理器..."

# 配置变量
PROJECT_DIR="/opt/video-learning-manager"
BACKUP_DIR="/opt/backups/video-learning-manager"
GITHUB_REPO="ghcr.io/your-username/video-learning-manager"  # 需要替换为实际仓库

# 检查Docker是否运行
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker未运行，请先启动Docker服务"
    exit 1
fi

# 创建备份
echo "💾 创建备份..."
sudo mkdir -p $BACKUP_DIR
BACKUP_NAME="backup-$(date +%Y%m%d-%H%M%S)"
sudo mkdir -p $BACKUP_DIR/$BACKUP_NAME

if [ -d "$PROJECT_DIR/data" ]; then
    sudo cp -r $PROJECT_DIR/data $BACKUP_DIR/$BACKUP_NAME/
    echo "✅ 数据库已备份到 $BACKUP_DIR/$BACKUP_NAME"
fi

# 创建项目目录
echo "📁 准备项目目录..."
sudo mkdir -p $PROJECT_DIR
sudo chown $(whoami):$(whoami) $PROJECT_DIR

# 创建数据目录
sudo mkdir -p $PROJECT_DIR/{data,uploads,videos,audios,thumbnails}
sudo chown -R $(whoami):$(whoami) $PROJECT_DIR

# 复制配置文件
echo "📋 复制配置文件..."
cp docker-compose.prod.yml $PROJECT_DIR/
cp nginx.conf $PROJECT_DIR/
cp .env.production $PROJECT_DIR/.env

# 登录GitHub Container Registry
echo "🔐 登录容器仓库..."
echo $GITHUB_TOKEN | docker login ghcr.io -u $GITHUB_USERNAME --password-stdin

# 拉取最新镜像
echo "📥 拉取最新镜像..."
cd $PROJECT_DIR
docker-compose -f docker-compose.prod.yml pull

# 停止旧服务
echo "🛑 停止旧服务..."
docker-compose -f docker-compose.prod.yml down || true

# 启动新服务
echo "🚀 启动新服务..."
docker-compose -f docker-compose.prod.yml up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 30

# 健康检查
echo "🔍 检查服务状态..."
HEALTH_CHECK_FAILED=0

# 检查后端
if curl -f http://localhost:8000/health >/dev/null 2>&1; then
    echo "✅ 后端服务正常"
else
    echo "❌ 后端服务异常"
    HEALTH_CHECK_FAILED=1
fi

# 检查前端
if curl -f http://localhost >/dev/null 2>&1; then
    echo "✅ 前端服务正常"
else
    echo "❌ 前端服务异常"
    HEALTH_CHECK_FAILED=1
fi

# 检查Redis
if docker exec video-manager-redis redis-cli ping >/dev/null 2>&1; then
    echo "✅ Redis服务正常"
else
    echo "❌ Redis服务异常"
    HEALTH_CHECK_FAILED=1
fi

# 清理旧镜像
echo "🧹 清理旧镜像..."
docker image prune -f
docker system prune -f

if [ $HEALTH_CHECK_FAILED -eq 0 ]; then
    echo ""
    echo "🎉 部署成功！"
    echo "🌐 应用地址: http://$(hostname -I | awk '{print $1}')"
    echo "📊 监控命令: docker-compose -f $PROJECT_DIR/docker-compose.prod.yml logs -f"
else
    echo ""
    echo "⚠️ 部署完成但存在异常，请检查日志:"
    echo "📊 查看日志: docker-compose -f $PROJECT_DIR/docker-compose.prod.yml logs"
fi

echo ""
echo "📋 有用的命令:"
echo "  重启服务: docker-compose -f $PROJECT_DIR/docker-compose.prod.yml restart"
echo "  查看日志: docker-compose -f $PROJECT_DIR/docker-compose.prod.yml logs -f [service_name]"
echo "  进入容器: docker exec -it video-manager-backend bash"
echo "  备份数据: cp -r $PROJECT_DIR/data $BACKUP_DIR/manual-$(date +%Y%m%d-%H%M%S)"