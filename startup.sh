#!/bin/bash

# 🚀 视频学习管理器 - 完整启动脚本
# 确保所有依赖、模型、权限都正确配置后启动项目

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

print_header "🚀 视频学习管理器完整启动流程"
print_header "==============================================="

# 步骤1: 环境检查和权限修复
step1_environment_check() {
    print_header "📋 步骤1: 环境检查和权限修复"
    
    print_status "检查Docker..."
    if ! command -v docker &> /dev/null; then
        print_error "Docker未安装！请先安装Docker"
        exit 1
    fi
    
    print_status "检查Docker Compose..."
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose未安装！请先安装Docker Compose"
        exit 1
    fi
    
    print_status "检查NVIDIA驱动..."
    if ! command -v nvidia-smi &> /dev/null; then
        print_error "NVIDIA驱动未安装！请先安装NVIDIA驱动"
        exit 1
    fi
    
    print_status "检查GPU Docker支持..."
    if docker run --rm --gpus all hello-world > /dev/null 2>&1; then
        print_success "✅ GPU Docker支持正常"
    else
        print_warning "⚠️ GPU Docker支持可能有问题，如果构建失败请安装nvidia-container-toolkit"
    fi
    
    print_success "✅ Docker和GPU环境检查通过"
    
    print_status "修复项目权限..."
    sudo chown -R $(whoami):$(whoami) . 2>/dev/null || true
    sudo chmod -R u+rwX . 2>/dev/null || true
    chmod +x *.sh 2>/dev/null || true
    
    print_success "✅ 权限修复完成"
}

# 步骤2: 代码更新
step2_code_update() {
    print_header "📥 步骤2: 代码更新"
    
    git config --global --add safe.directory $(pwd) 2>/dev/null || true
    
    print_status "保存本地修改..."
    git stash 2>/dev/null || true
    
    print_status "拉取最新代码..."
    if git pull origin main; then
        print_success "✅ 代码更新成功"
    else
        print_warning "⚠️ 代码拉取失败，继续使用当前版本"
    fi
}

# 步骤3: 检查基础镜像
step3_base_images() {
    print_header "📦 步骤3: 检查基础镜像"
    
    # 检查CUDA镜像
    if docker images nvidia/cuda:11.8.0-devel-ubuntu22.04 | grep -q "11.8.0-devel-ubuntu22.04"; then
        print_success "✅ CUDA镜像已存在"
    else
        print_status "拉取NVIDIA CUDA基础镜像..."
        docker pull nvidia/cuda:11.8.0-devel-ubuntu22.04
        print_success "✅ CUDA镜像就绪"
    fi
    
    # 检查其他镜像
    docker images nginx:alpine | grep -q "alpine" || docker pull nginx:alpine
    docker images node:18-alpine | grep -q "18-alpine" || docker pull node:18-alpine
    
    print_success "✅ 基础镜像检查完成"
}

# 步骤4: 构建镜像
step4_build_and_models() {
    print_header "🔧 步骤4: 构建应用镜像"
    
    print_status "停止现有服务..."
    docker-compose -f docker-compose.gpu.yml down 2>/dev/null || true
    
    # 检查是否需要重新构建
    if docker images video-learning-manager-video-learning-manager-gpu | grep -q "latest"; then
        print_status "检测到现有镜像，使用缓存构建..."
        docker-compose -f docker-compose.gpu.yml build
    else
        print_status "首次构建，创建应用镜像..."
        docker-compose -f docker-compose.gpu.yml build
    fi
    
    print_success "✅ 应用镜像构建完成"
}

# 步骤5: 模型验证
step5_model_verification() {
    print_header "🤖 步骤5: 模型验证"
    
    print_status "验证模型是否正确安装..."
    
    if docker run --rm --gpus all video-learning-manager-video-learning-manager-gpu \
        python3.11 -c "
from faster_whisper import WhisperModel
print('🧪 验证本地large-v3模型...')
model = WhisperModel('/root/.cache/huggingface/hub/models--Systran--faster-whisper-large-v3', device='cuda', compute_type='float16')
print('✅ 本地large-v3模型可用')
print('🎉 模型验证通过！')
"; then
        print_success "✅ 模型验证通过"
    else
        print_error "❌ 模型验证失败"
        exit 1
    fi
}

# 步骤6: 启动服务
step6_start_services() {
    print_header "🚀 步骤6: 启动所有服务"
    
    print_status "启动Docker Compose服务..."
    docker-compose -f docker-compose.gpu.yml up -d
    
    print_status "等待服务启动..."
    max_attempts=60
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            print_success "✅ 后端服务已启动"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            print_error "❌ 后端服务启动超时"
            docker logs video-learning-manager-gpu --tail=20
            exit 1
        fi
        
        echo -n "."
        sleep 2
        ((attempt++))
    done
    
    sleep 5
    if curl -s http://localhost/ > /dev/null 2>&1; then
        print_success "✅ 前端服务已启动"
    else
        print_warning "⚠️ 前端服务可能有问题"
    fi
}

# 步骤7: 最终验证
step7_final_verification() {
    print_header "✅ 步骤7: 最终验证"
    
    print_status "测试API接口..."
    if curl -s http://localhost:8000/api/local-videos/list > /dev/null 2>&1; then
        print_success "✅ 本地视频API正常"
    else
        print_warning "⚠️ API可能有问题"
    fi
    
    print_status "检查GPU状态..."
    if nvidia-smi > /dev/null 2>&1; then
        gpu_usage=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits)
        print_success "✅ GPU状态正常，使用率: ${gpu_usage}%"
    else
        print_warning "⚠️ GPU检查失败"
    fi
    
    docker-compose -f docker-compose.gpu.yml ps
}

# 显示完成信息
show_completion_info() {
    print_header "🎉 启动完成！"
    echo ""
    echo "📊 访问地址:"
    echo "  🌐 前端界面: http://$(hostname -I | awk '{print $1}')"
    echo "  🔧 后端API: http://$(hostname -I | awk '{print $1}'):8000"
    echo "  📚 API文档: http://$(hostname -I | awk '{print $1}'):8000/docs"
    echo ""
    echo "🎯 模型配置:"
    echo "  🎯 使用模型: faster-whisper-large-v3（GPU加速）"
    echo ""
    echo "🔧 常用命令:"
    echo "  📊 查看状态: docker-compose -f docker-compose.gpu.yml ps"
    echo "  📝 查看日志: docker-compose -f docker-compose.gpu.yml logs -f"
    echo "  🔄 重启服务: ./deploy.sh hot"
}

# 主执行流程
main() {
    echo "开始执行完整启动流程..."
    echo ""
    
    step1_environment_check
    step2_code_update  
    step3_base_images
    step4_build_and_models
    step5_model_verification
    step6_start_services
    step7_final_verification
    
    show_completion_info
    
    print_success "🎯 系统完全就绪！可以开始使用视频转录功能"
}

# 执行主流程
main "$@"