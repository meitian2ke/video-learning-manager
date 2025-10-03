#!/bin/bash

# 🚀 视频学习管理器 - 统一管理脚本
# 集成所有功能：部署、更新、模型管理、监控等

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
    print_header "🚀 视频学习管理器 - 统一管理脚本"
    echo ""
    echo "使用方式:"
    echo "  ./run.sh start      - 启动服务"
    echo "  ./run.sh stop       - 停止服务"
    echo "  ./run.sh restart    - 重启服务"
    echo "  ./run.sh update     - 更新代码并重启（推荐）"
    echo "  ./run.sh rebuild    - 完全重构"
    echo "  ./run.sh logs       - 查看日志"
    echo "  ./run.sh status     - 查看状态"
    echo "  ./run.sh models     - 模型管理"
    echo "  ./run.sh clean      - 清理资源"
    echo ""
    exit 0
}

# 系统检查
check_requirements() {
    print_status "检查系统要求..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker未安装！"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! command -v "docker compose" &> /dev/null; then
        print_error "Docker Compose未安装！"
        exit 1
    fi
    
    # 统一使用 docker compose（新版）或 docker-compose（旧版）
    if command -v "docker compose" &> /dev/null; then
        DOCKER_COMPOSE="docker compose"
    else
        DOCKER_COMPOSE="docker-compose"
    fi
    
    if ! command -v nvidia-smi &> /dev/null; then
        print_error "NVIDIA驱动未安装！"
        exit 1
    fi
    
    print_success "系统要求检查通过"
}

# 更新代码
update_code() {
    print_status "拉取最新代码..."
    git stash 2>/dev/null || true
    if git pull origin main; then
        print_success "代码更新成功"
    else
        print_warning "代码更新失败，继续使用当前版本"
    fi
}

# 检查模型
check_models() {
    print_status "检查Whisper模型..."
    if [ -d "./models/faster-whisper-large-v3" ]; then
        print_success "✅ 本地模型存在"
        return 0
    else
        print_warning "⚠️ 本地模型不存在: ./models/faster-whisper-large-v3"
        print_warning "请先下载模型或从其他位置复制"
        return 1
    fi
}

# 启动服务
start_service() {
    print_header "🚀 启动视频学习管理器"
    
    check_requirements
    check_models || exit 1
    
    print_status "启动Docker Compose服务..."
    $DOCKER_COMPOSE -f docker-compose.gpu.yml up -d
    
    print_status "等待服务启动..."
    sleep 10
    
    # 健康检查
    max_attempts=30
    attempt=1
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            print_success "✅ 后端服务已启动"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            print_error "❌ 服务启动超时"
            show_logs
            exit 1
        fi
        
        echo -n "."
        sleep 2
        ((attempt++))
    done
    
    # 检查前端
    if curl -s http://localhost/ > /dev/null 2>&1; then
        print_success "✅ 前端服务已启动"
    else
        print_warning "⚠️ 前端服务可能有问题"
    fi
    
    show_status
}

# 停止服务
stop_service() {
    print_header "🛑 停止服务"
    check_requirements
    
    print_status "停止所有容器..."
    $DOCKER_COMPOSE -f docker-compose.gpu.yml down
    print_success "服务已停止"
}

# 重启服务
restart_service() {
    print_header "🔄 重启服务"
    stop_service
    start_service
}

# 更新服务
update_service() {
    print_header "📦 更新服务"
    check_requirements
    update_code
    
    print_status "停止现有服务..."
    $DOCKER_COMPOSE -f docker-compose.gpu.yml down
    
    print_status "重新构建镜像..."
    $DOCKER_COMPOSE -f docker-compose.gpu.yml build
    
    start_service
    print_success "更新完成！"
}

# 完全重构
rebuild_service() {
    print_header "🔧 完全重构"
    check_requirements
    update_code
    
    print_status "停止所有服务..."
    $DOCKER_COMPOSE -f docker-compose.gpu.yml down
    
    print_status "清理Docker资源..."
    docker system prune -f
    
    print_status "无缓存重新构建..."
    $DOCKER_COMPOSE -f docker-compose.gpu.yml build --no-cache
    
    start_service
    print_success "重构完成！"
}

# 查看日志
show_logs() {
    print_header "📋 服务日志"
    check_requirements
    
    echo "选择要查看的服务日志："
    echo "1) 所有服务"
    echo "2) 后端服务"
    echo "3) 前端服务"
    read -p "请选择 (1-3): " choice
    
    case $choice in
        1) $DOCKER_COMPOSE -f docker-compose.gpu.yml logs -f ;;
        2) $DOCKER_COMPOSE -f docker-compose.gpu.yml logs -f video-learning-manager-gpu ;;
        3) $DOCKER_COMPOSE -f docker-compose.gpu.yml logs -f frontend ;;
        *) $DOCKER_COMPOSE -f docker-compose.gpu.yml logs -f ;;
    esac
}

# 查看状态
show_status() {
    print_header "📊 服务状态"
    
    echo ""
    echo "📦 Docker容器状态:"
    $DOCKER_COMPOSE -f docker-compose.gpu.yml ps
    
    echo ""
    echo "🌐 服务地址:"
    local ip=$(hostname -I | awk '{print $1}')
    echo "  前端界面: http://$ip"
    echo "  后端API:  http://$ip:8000"
    echo "  API文档:  http://$ip:8000/docs"
    
    echo ""
    echo "💻 GPU状态:"
    if command -v nvidia-smi &> /dev/null; then
        nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits | head -1
    else
        echo "  NVIDIA驱动未安装"
    fi
    
    echo ""
    echo "📊 快速测试:"
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "  ✅ 后端健康检查通过"
    else
        echo "  ❌ 后端健康检查失败"
    fi
    
    if curl -s http://localhost/ > /dev/null 2>&1; then
        echo "  ✅ 前端访问正常"
    else
        echo "  ❌ 前端访问失败"
    fi
}

# 模型管理
manage_models() {
    print_header "🤖 模型管理"
    
    echo ""
    echo "模型管理选项："
    echo "1) 检查模型状态"
    echo "2) 验证模型功能"
    echo "3) 模型信息"
    read -p "请选择 (1-3): " choice
    
    case $choice in
        1)
            if [ -d "./models/faster-whisper-large-v3" ]; then
                print_success "✅ 模型目录存在"
                du -sh ./models/faster-whisper-large-v3 2>/dev/null || echo "无法获取大小"
            else
                print_error "❌ 模型目录不存在"
                echo "请将模型放置在: ./models/faster-whisper-large-v3/"
            fi
            ;;
        2)
            print_status "验证模型功能..."
            if curl -s http://localhost:8000/api/local-videos/model-status > /dev/null 2>&1; then
                curl -s http://localhost:8000/api/local-videos/model-status | python3 -m json.tool 2>/dev/null || echo "API响应格式错误"
            else
                print_error "后端服务未运行，请先启动服务"
            fi
            ;;
        3)
            echo "模型配置信息:"
            echo "  模型名称: faster-whisper-large-v3"
            echo "  设备类型: CUDA GPU"
            echo "  计算类型: float16"
            echo "  本地路径: ./models/faster-whisper-large-v3"
            ;;
    esac
}

# 清理资源
clean_resources() {
    print_header "🧹 清理资源"
    
    print_warning "这将清理Docker缓存和未使用的镜像"
    read -p "确认继续? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "清理Docker资源..."
        docker system prune -f
        docker image prune -f
        print_success "清理完成"
    else
        print_status "清理已取消"
    fi
}

# 主函数
main() {
    case "${1:-}" in
        start)
            start_service
            ;;
        stop)
            stop_service
            ;;
        restart)
            restart_service
            ;;
        update)
            update_service
            ;;
        rebuild)
            rebuild_service
            ;;
        logs)
            show_logs
            ;;
        status)
            show_status
            ;;
        models)
            manage_models
            ;;
        clean)
            clean_resources
            ;;
        --help|-h|help|"")
            show_help
            ;;
        *)
            print_error "未知命令: $1"
            show_help
            ;;
    esac
}

# 执行主函数
main "$@"