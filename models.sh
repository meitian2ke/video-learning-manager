#!/bin/bash

# 🤖 Whisper模型管理脚本
# 使用Docker Compose管理模型下载和验证

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

show_help() {
    echo "🤖 Whisper模型管理脚本"
    echo ""
    echo "使用方式:"
    echo "  ./models.sh download  - 下载Whisper模型"
    echo "  ./models.sh verify    - 验证模型是否可用"
    echo "  ./models.sh status    - 查看模型状态"
    echo "  ./models.sh clean     - 清理模型缓存"
    echo ""
    exit 0
}

# 下载模型
download_models() {
    print_status "🤖 开始下载Whisper模型..."
    
    # 构建模型下载镜像
    print_status "构建模型下载镜像..."
    docker-compose -f docker-compose.gpu.yml build whisper-models
    
    # 运行模型下载
    print_status "运行模型下载容器..."
    docker-compose -f docker-compose.gpu.yml --profile init run --rm whisper-models
    
    print_success "✅ 模型下载完成！"
}

# 验证模型
verify_models() {
    print_status "🧪 验证模型可用性..."
    
    # 检查卷是否存在
    if ! docker volume inspect video-learning-manager_whisper-models > /dev/null 2>&1; then
        print_error "❌ 模型卷不存在，请先下载模型"
        echo "运行: ./models.sh download"
        return 1
    fi
    
    # 运行验证
    docker run --rm \
        --gpus all \
        -v video-learning-manager_whisper-models:/root/.cache/huggingface \
        -e HF_HOME=/root/.cache/huggingface \
        video-learning-manager-whisper-models \
        python3 -c "
from faster_whisper import WhisperModel
try:
    model = WhisperModel('base', device='cuda', compute_type='float16')
    print('✅ 模型验证成功，GPU转录功能就绪！')
except Exception as e:
    print(f'❌ 模型验证失败: {e}')
    exit(1)
"
    
    print_success "🚀 模型验证通过！"
}

# 查看模型状态
show_status() {
    print_status "📊 模型状态检查..."
    
    # 检查卷
    if docker volume inspect video-learning-manager_whisper-models > /dev/null 2>&1; then
        print_success "✅ 模型卷存在"
        
        # 显示卷大小
        volume_size=$(docker run --rm -v video-learning-manager_whisper-models:/data alpine du -sh /data | cut -f1)
        print_status "模型缓存大小: $volume_size"
        
        # 列出模型文件
        print_status "模型文件列表:"
        docker run --rm -v video-learning-manager_whisper-models:/data alpine ls -la /data/hub/ 2>/dev/null || echo "  无模型文件"
        
    else
        print_warning "❌ 模型卷不存在"
    fi
    
    # 检查运行中的服务
    if docker ps | grep -q video-learning-manager-gpu; then
        print_success "✅ 后端服务正在运行"
    else
        print_warning "⚠️ 后端服务未运行"
    fi
}

# 清理模型缓存
clean_models() {
    print_warning "⚠️ 这将删除所有已下载的模型！"
    read -p "确认继续? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "清理模型缓存..."
        docker volume rm video-learning-manager_whisper-models 2>/dev/null || true
        print_success "✅ 模型缓存已清理"
    else
        print_status "操作已取消"
    fi
}

# 主函数
main() {
    case "${1:-}" in
        download)
            download_models
            ;;
        verify)
            verify_models
            ;;
        status)
            show_status
            ;;
        clean)
            clean_models
            ;;
        --help|-h|"")
            show_help
            ;;
        *)
            print_error "未知命令: $1"
            show_help
            ;;
    esac
}

echo "🤖 Whisper模型管理脚本"
echo "=============================================="

main "$@"