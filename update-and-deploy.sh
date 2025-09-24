#!/bin/bash

# 一键更新部署脚本
# 拉取代码 -> 停止服务 -> 重新构建 -> 启动服务

set -e

echo "🚀 开始一键更新部署..."

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

# 获取参数
FORCE_REBUILD=${1:-"false"}  # 是否强制重新构建
SKIP_BUILD=${2:-"false"}     # 是否跳过构建（仅热更新）

print_status "部署参数: 强制重构=$FORCE_REBUILD, 跳过构建=$SKIP_BUILD"

# 1. 拉取最新代码
print_status "1. 拉取最新代码..."
git stash 2>/dev/null || true  # 暂存本地修改
if git pull origin main; then
    print_success "代码更新成功"
else
    print_error "代码更新失败"
    exit 1
fi

# 2. 检查服务状态
print_status "2. 检查当前服务状态..."
docker-compose -f docker-compose.gpu.yml ps

# 3. 根据参数选择更新方式
if [ "$SKIP_BUILD" = "true" ]; then
    # 热更新模式 - 不重新构建，直接替换文件
    print_status "🔥 热更新模式: 直接替换代码文件..."
    
    # 检查容器是否运行
    if docker ps | grep -q video-learning-manager-gpu; then
        print_status "替换后端代码文件..."
        docker cp backend/app/api/local_videos.py video-learning-manager-gpu:/app/backend/app/api/ 2>/dev/null || true
        docker cp backend/app/api/system_monitor.py video-learning-manager-gpu:/app/backend/app/api/ 2>/dev/null || true
        docker cp backend/app/api/gpu_monitor.py video-learning-manager-gpu:/app/backend/app/api/ 2>/dev/null || true
        docker cp backend/app/core/config.py video-learning-manager-gpu:/app/backend/app/core/ 2>/dev/null || true
        
        # 重启后端容器
        print_status "重启后端容器..."
        docker restart video-learning-manager-gpu
        
        print_success "热更新完成！"
    else
        print_warning "后端容器未运行，切换到完整重启模式"
        SKIP_BUILD="false"
    fi
fi

if [ "$SKIP_BUILD" = "false" ]; then
    # 完整重新部署模式
    print_status "🔧 完整重新部署模式..."
    
    # 4. 停止现有服务
    print_status "4. 停止现有服务..."
    docker-compose -f docker-compose.gpu.yml down
    print_success "服务已停止"
    
    # 5. 清理资源（可选）
    if [ "$FORCE_REBUILD" = "true" ]; then
        print_status "5. 清理Docker资源..."
        docker system prune -f
        print_success "资源清理完成"
    else
        print_status "5. 跳过资源清理（使用缓存加速）"
    fi
    
    # 6. 构建镜像
    print_status "6. 构建镜像..."
    if [ "$FORCE_REBUILD" = "true" ]; then
        print_warning "强制重新构建（无缓存）..."
        docker-compose -f docker-compose.gpu.yml build --no-cache
    else
        print_status "使用缓存构建..."
        docker-compose -f docker-compose.gpu.yml build
    fi
    print_success "镜像构建完成"
    
    # 7. 启动服务
    print_status "7. 启动服务..."
    docker-compose -f docker-compose.gpu.yml up -d
    print_success "服务启动完成"
fi

# 8. 等待服务就绪
print_status "8. 等待服务就绪..."
max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        print_success "后端服务已就绪！"
        break
    fi
    
    if [ $attempt -eq $max_attempts ]; then
        print_error "服务启动超时！"
        echo ""
        print_status "查看服务状态:"
        docker-compose -f docker-compose.gpu.yml ps
        echo ""
        print_status "查看后端日志:"
        docker logs video-learning-manager-gpu --tail=20
        exit 1
    fi
    
    echo -n "."
    sleep 2
    ((attempt++))
done

# 前端健康检查
if curl -s http://localhost/ > /dev/null 2>&1; then
    print_success "前端服务已就绪！"
else
    print_warning "前端服务可能有问题，请检查"
fi

# 9. 显示服务信息
print_success "🎉 更新部署成功！"
echo ""
echo "📊 服务信息:"
echo "  - 🌐 前端界面: http://$(hostname -I | awk '{print $1}') (端口80)"
echo "  - 🔧 后端API: http://$(hostname -I | awk '{print $1}'):8000"
echo "  - 📊 GPU监控: http://$(hostname -I | awk '{print $1}')/api/gpu/status"
echo "  - 📈 处理状态: http://$(hostname -I | awk '{print $1}'):8000/api/local-videos/processing-status"
echo ""
echo "🔧 管理命令:"
echo "  - 查看日志: docker-compose -f docker-compose.gpu.yml logs -f"
echo "  - 查看状态: docker-compose -f docker-compose.gpu.yml ps"
echo "  - 重启服务: docker-compose -f docker-compose.gpu.yml restart"
echo ""
echo "🚀 快速更新选项:"
echo "  - 热更新（推荐）: ./update-and-deploy.sh false true"
echo "  - 常规更新: ./update-and-deploy.sh"
echo "  - 强制重构: ./update-and-deploy.sh true"
echo ""

# 10. 运行服务验证
print_status "10. 验证核心功能..."
echo ""

# 测试API
if api_response=$(curl -s http://localhost:8000/api/local-videos/list 2>/dev/null); then
    video_count=$(echo "$api_response" | grep -o '"total_count":[0-9]*' | cut -d':' -f2 || echo "0")
    print_success "✅ 本地视频API正常，发现 $video_count 个视频"
else
    print_warning "⚠️ 本地视频API响应异常"
fi

# 测试GPU状态
if curl -s http://localhost:8000/api/monitor/lite > /dev/null 2>&1; then
    print_success "✅ 系统监控API正常"
else
    print_warning "⚠️ 系统监控API响应异常"
fi

# GPU检查
if nvidia-smi > /dev/null 2>&1; then
    gpu_usage=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits)
    print_success "✅ GPU状态正常，使用率: ${gpu_usage}%"
else
    print_warning "⚠️ GPU检查失败"
fi

echo ""
print_success "🎯 所有服务已更新并运行！可以开始测试视频处理功能。"