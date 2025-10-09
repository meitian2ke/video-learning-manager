#!/bin/bash

# 🚀 视频学习管理器 - 统一部署脚本
# 支持首次部署、热更新、常规更新、完全重构
# 
# 使用方式:
#   ./deploy.sh          - 首次部署或常规更新
#   ./deploy.sh hot      - 热更新（推荐，2-3分钟）
#   ./deploy.sh update   - 常规更新（5-10分钟）  
#   ./deploy.sh rebuild  - 完全重构（15-30分钟）
#   ./deploy.sh --help   - 显示帮助

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_header() { echo -e "${CYAN}$1${NC}"; }

show_help() {
    echo "🚀 视频学习管理器部署脚本"
    echo ""
    echo "使用方式:"
    echo "  ./deploy.sh          首次部署或常规更新"
    echo "  ./deploy.sh hot      热更新（推荐，2-3分钟）"
    echo "  ./deploy.sh update   常规更新（5-10分钟）"
    echo "  ./deploy.sh rebuild  完全重构（15-30分钟）"
    echo ""
    echo "更新方式说明:"
    echo "  🔥 hot     - 只替换代码文件，重启容器"
    echo "  📦 update  - 重新构建（使用缓存）"
    echo "  🔧 rebuild - 清理缓存，完全重构"
    echo ""
    echo "详细文档: 查看 DEPLOY.md"
    exit 0
}

# 获取部署模式
MODE=${1:-"update"}
case $MODE in
    --help|-h) show_help ;;
    hot|update|rebuild) ;;
    *) print_warning "未知模式 '$MODE'，使用默认 'update' 模式"; MODE="update" ;;
esac

print_header "==============================================="
print_header "🚀 视频学习管理器 GPU 部署脚本"
print_header "模式: $MODE"
print_header "==============================================="

# 检查系统要求
check_requirements() {
    print_status "检查系统要求..."
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker未安装！请先安装Docker"
        exit 1
    fi
    
    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose未安装！请先安装Docker Compose"
        exit 1
    fi
    
    # 检查NVIDIA驱动
    if ! command -v nvidia-smi &> /dev/null; then
        print_error "NVIDIA驱动未安装！请先安装NVIDIA驱动"
        exit 1
    fi
    
    print_success "系统要求检查通过！"
}

# 拉取代码（强制同步远程 main 分支）
update_code() {
    print_status "拉取最新代码..."

    # 先暂存当前修改（避免报错，但我们不会再恢复 stash）
    git stash push --include-untracked -m "auto-stash-before-update" >/dev/null 2>&1 || true

    # 强制同步远程仓库
    if git fetch origin main && git reset --hard origin/main; then
        print_success "代码更新成功 ✅（已强制与远程 main 同步）"
    else
        print_error "代码更新失败 ❌"
        exit 1
    fi
}

# 热更新模式
hot_update() {
    print_header "🔥 热更新模式 - 快速替换代码文件"
    
    if ! docker ps | grep -q video-learning-manager-gpu; then
        print_warning "后端容器未运行，切换到常规更新模式"
        return 1
    fi
    
    print_status "替换后端代码文件..."
    docker cp backend/app/api/local_videos.py video-learning-manager-gpu:/app/backend/app/api/ 2>/dev/null || true
    docker cp backend/app/api/system_monitor.py video-learning-manager-gpu:/app/backend/app/api/ 2>/dev/null || true
    docker cp backend/app/api/gpu_monitor.py video-learning-manager-gpu:/app/backend/app/api/ 2>/dev/null || true
    docker cp backend/app/core/config.py video-learning-manager-gpu:/app/backend/app/core/ 2>/dev/null || true
    
    print_status "重启后端容器..."
    docker restart video-learning-manager-gpu
    
    print_success "热更新完成！"
    return 0
}

# 常规更新模式
regular_update() {
    print_header "📦 常规更新模式 - 重新构建（使用缓存）"
    
    print_status "停止现有服务..."
    docker-compose -f docker-compose.gpu.yml down
    
    print_status "构建镜像（使用缓存）..."
    if ! docker-compose -f docker-compose.gpu.yml build; then
        print_warning "构建失败，可能是网络问题，尝试热更新..."
        if hot_update; then
            return 0
        else
            print_error "构建和热更新都失败了"
            exit 1
        fi
    fi
    
    print_status "初始化Whisper模型..."
    if ! docker volume inspect video-learning-manager_whisper-models > /dev/null 2>&1; then
        print_status "首次运行，下载Whisper模型..."
        docker-compose -f docker-compose.gpu.yml --profile init run --rm whisper-models
    else
        print_success "Whisper模型已存在，跳过下载"
    fi
    
    print_status "启动服务..."
    docker-compose -f docker-compose.gpu.yml up -d
    
    print_success "常规更新完成！"
}

# 完全重构模式
full_rebuild() {
    print_header "🔧 完全重构模式 - 清理缓存并重构"
    
    print_status "停止现有服务..."
    docker-compose -f docker-compose.gpu.yml down
    
    print_status "清理Docker资源（保留模型数据）..."
    docker system prune -f
    
    print_status "强制重新构建（无缓存）..."
    docker-compose -f docker-compose.gpu.yml build --no-cache
    
    print_status "重新下载Whisper模型..."
    docker-compose -f docker-compose.gpu.yml --profile init run --rm whisper-models
    
    print_status "启动服务..."
    docker-compose -f docker-compose.gpu.yml up -d
    
    print_success "完全重构完成！"
}

# 等待服务就绪
wait_for_services() {
    print_status "等待服务就绪..."
    max_attempts=30
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            print_success "后端服务已就绪！"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            print_error "服务启动超时！"
            print_status "查看服务状态:"
            docker-compose -f docker-compose.gpu.yml ps
            print_status "查看后端日志:"
            docker logs video-learning-manager-gpu --tail=20
            exit 1
        fi
        
        echo -n "."
        sleep 2
        ((attempt++))
    done
    
    # 前端检查
    if curl -s http://localhost/ > /dev/null 2>&1; then
        print_success "前端服务已就绪！"
    else
        print_warning "前端服务可能有问题，请检查"
    fi
}

# 验证功能
verify_services() {
    print_status "验证核心功能..."
    
    # API测试
    if api_response=$(curl -s http://localhost:8000/api/local-videos/list 2>/dev/null); then
        video_count=$(echo "$api_response" | grep -o '"total_count":[0-9]*' | cut -d':' -f2 || echo "0")
        print_success "✅ 本地视频API正常，发现 $video_count 个视频"
    else
        print_warning "⚠️ 本地视频API响应异常"
    fi
    
    # GPU检查
    if nvidia-smi > /dev/null 2>&1; then
        gpu_usage=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits)
        print_success "✅ GPU状态正常，使用率: ${gpu_usage}%"
    else
        print_warning "⚠️ GPU检查失败"
    fi
}

# 显示部署信息
show_deployment_info() {
    print_success "🎉 部署成功！"
    echo ""
    echo "📊 服务信息:"
    echo "  - 🌐 前端界面: http://$(hostname -I | awk '{print $1}') (端口80)"
    echo "  - 🔧 后端API: http://$(hostname -I | awk '{print $1}'):8000"
    echo "  - 📚 API文档: http://$(hostname -I | awk '{print $1}'):8000/docs"
    echo "  - 📊 GPU监控: http://$(hostname -I | awk '{print $1}')/api/gpu/status"
    echo ""
    echo "🔧 管理命令:"
    echo "  - 查看日志: docker-compose -f docker-compose.gpu.yml logs -f"
    echo "  - 查看状态: docker-compose -f docker-compose.gpu.yml ps"
    echo "  - 重启服务: docker-compose -f docker-compose.gpu.yml restart"
    echo ""
    echo "🚀 下次更新使用:"
    echo "  - 热更新（推荐）: ./deploy.sh hot"
    echo "  - 常规更新: ./deploy.sh update"  
    echo "  - 完全重构: ./deploy.sh rebuild"
}

# 主流程
main() {
    # 系统检查
    check_requirements
    
    # 拉取代码
    update_code
    
    # 根据模式执行部署
    case $MODE in
        "hot")
            if ! hot_update; then
                print_warning "热更新失败，切换到常规更新模式"
                regular_update
            fi
            ;;
        "update")
            regular_update
            ;;
        "rebuild")
            full_rebuild
            ;;
    esac
    
    # 等待服务
    wait_for_services
    
    # 验证功能
    verify_services
    
    # 显示信息
    show_deployment_info
    
    print_success "🎯 部署完成！可以开始使用视频处理功能。"
}

# 执行主流程
main "$@"