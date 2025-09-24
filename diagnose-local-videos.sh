#!/bin/bash

# 本地视频问题诊断脚本

set -e

echo "🔍 本地视频问题诊断..."

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "================================"

# 1. 检查本地目录
print_status "1. 检查本地local-videos目录..."
if [ -d "local-videos" ]; then
    print_success "local-videos目录存在"
    echo "目录内容:"
    ls -la local-videos/
    
    video_count=$(find local-videos/ -name "*.mp4" -o -name "*.avi" -o -name "*.mov" -o -name "*.mkv" | wc -l)
    echo "视频文件数量: $video_count"
else
    print_error "local-videos目录不存在"
    mkdir -p local-videos
    print_success "已创建local-videos目录"
fi

echo ""

# 2. 检查容器状态
print_status "2. 检查Docker容器状态..."
if docker-compose -f docker-compose.gpu.yml ps | grep -q "Up"; then
    print_success "容器正在运行"
    docker-compose -f docker-compose.gpu.yml ps
else
    print_error "容器未运行或有问题"
    docker-compose -f docker-compose.gpu.yml ps
fi

echo ""

# 3. 检查容器内目录映射
print_status "3. 检查容器内目录映射..."
if docker exec video-learning-manager-gpu test -d /app/local-videos; then
    print_success "容器内目录存在"
    echo "容器内目录内容:"
    docker exec video-learning-manager-gpu ls -la /app/local-videos/
else
    print_error "容器内目录不存在"
fi

echo ""

# 4. 检查API连通性
print_status "4. 检查API连通性..."

# 健康检查
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    print_success "后端API健康检查通过"
else
    print_error "后端API无响应"
fi

# 本地视频API
if curl -s http://localhost:8000/api/local-videos/list > /dev/null 2>&1; then
    print_success "本地视频API可访问"
    echo "API响应:"
    curl -s http://localhost:8000/api/local-videos/list | head -10
else
    print_error "本地视频API无响应"
fi

echo ""

# 5. 检查后端日志
print_status "5. 检查后端日志（最近20行）..."
docker logs video-learning-manager-gpu --tail=20

echo ""

# 6. 检查前端访问
print_status "6. 检查前端访问..."
if curl -s http://localhost/ > /dev/null 2>&1; then
    print_success "前端可访问"
else
    print_error "前端无响应"
fi

echo ""

# 7. 检查系统监控API
print_status "7. 检查系统监控API..."
if curl -s http://localhost:8000/api/monitor/lite > /dev/null 2>&1; then
    print_success "系统监控API可访问"
    echo "监控数据:"
    curl -s http://localhost:8000/api/monitor/lite
else
    print_error "系统监控API无响应"
fi

echo ""
echo "================================"
print_status "诊断完成！"

echo ""
echo "🔧 可能的解决方案："
echo "1. 如果容器未运行: docker-compose -f docker-compose.gpu.yml up -d"
echo "2. 如果权限问题: chmod -R 755 local-videos/"
echo "3. 如果API无响应: 检查后端日志找出具体错误"
echo "4. 如果前端无响应: docker logs video-learning-frontend"