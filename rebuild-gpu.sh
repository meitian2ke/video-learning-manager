#!/bin/bash

# 快速重新部署脚本 - 使用缓存加速

set -e

echo "🔄 快速重新部署GPU版本..."

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# 1. 停止现有服务
print_status "停止现有服务..."
docker-compose -f docker-compose.gpu.yml down

# 2. 拉取代码更新
print_status "拉取最新代码..."
git pull origin main

# 3. 快速构建（使用缓存）
print_status "快速构建镜像（使用缓存）..."
docker-compose -f docker-compose.gpu.yml build

# 4. 启动服务
print_status "启动服务..."
docker-compose -f docker-compose.gpu.yml up -d

# 5. 等待服务就绪
print_status "等待服务启动..."
sleep 10

if curl -s http://localhost/health > /dev/null 2>&1; then
    print_success "✅ 服务启动成功！"
    echo ""
    echo "📊 服务信息:"
    echo "  - 前端界面: http://$(hostname -I | awk '{print $1}')"
    echo "  - 后端API: http://$(hostname -I | awk '{print $1}'):8000"
else
    echo "❌ 服务启动失败，请检查日志："
    echo "docker-compose -f docker-compose.gpu.yml logs"
fi