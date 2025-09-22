#!/bin/bash

# 生产环境GPU部署脚本
# 适用于配备NVIDIA GPU的Debian服务器

set -e

echo "🚀 开始部署视频学习管理器GPU版本..."

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# 1. 检查系统要求
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

# 检查nvidia-container-toolkit
# 检查nvidia-container-toolkit
if ! docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi >/dev/null 2>&1 && \
   ! docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi >/dev/null 2>&1; then
    print_error "nvidia-container-toolkit未正确配置！（nvidia-smi 检测失败）"
    exit 1
fi

print_success "系统要求检查通过！"

# 2. 检查GPU信息
print_status "检查GPU信息..."
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader,nounits
print_success "GPU检查完成"

# 3. 创建必要目录
print_status "创建数据目录..."
mkdir -p data/uploads data/videos data/audios data/thumbnails data/local-videos logs
chmod -R 755 data logs
print_success "目录创建完成"

# 4. 检查端口占用
print_status "检查端口占用..."
if lsof -i:8000 &> /dev/null; then
    print_warning "端口8000已被占用"
    read -p "是否强制停止占用端口的进程？(y/N): " force_stop
    if [[ $force_stop =~ ^[Yy]$ ]]; then
        sudo lsof -ti:8000 | xargs sudo kill -9
        print_success "端口已释放"
    else
        print_error "请手动释放端口8000后重新运行"
        exit 1
    fi
fi

# 5. 停止现有容器
print_status "停止现有容器..."
docker-compose -f docker-compose.gpu.yml down --remove-orphans 2>/dev/null || true
print_success "现有容器已停止"

# 6. 构建镜像
print_status "构建GPU优化镜像（使用国内镜像源加速）..."
docker-compose -f docker-compose.gpu.yml build --no-cache
print_success "镜像构建完成"

# 7. 启动服务
print_status "启动GPU服务..."
docker-compose -f docker-compose.gpu.yml up -d
print_success "服务启动完成"

# 8. 等待服务就绪
print_status "等待服务启动..."
max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        print_success "服务已就绪！"
        break
    fi
    
    if [ $attempt -eq $max_attempts ]; then
        print_error "服务启动超时！"
        print_status "查看容器日志:"
        docker-compose -f docker-compose.gpu.yml logs --tail=50
        exit 1
    fi
    
    echo -n "."
    sleep 2
    ((attempt++))
done

# 9. 显示部署信息
print_success "🎉 GPU版本部署成功！"
echo ""
echo "📊 服务信息:"
echo "  - 前端地址: http://$(hostname -I | awk '{print $1}'):8000"
echo "  - API文档: http://$(hostname -I | awk '{print $1}'):8000/docs"
echo "  - 健康检查: http://$(hostname -I | awk '{print $1}'):8000/health"
echo "  - GPU监控: http://$(hostname -I | awk '{print $1}'):9835 (如果启用)"
echo ""
echo "🔧 管理命令:"
echo "  - 查看日志: docker-compose -f docker-compose.gpu.yml logs -f"
echo "  - 停止服务: docker-compose -f docker-compose.gpu.yml down"
echo "  - 重启服务: docker-compose -f docker-compose.gpu.yml restart"
echo "  - 查看状态: docker-compose -f docker-compose.gpu.yml ps"
echo ""
echo "📈 性能监控:"
echo "  - GPU使用: nvidia-smi"
echo "  - 容器状态: docker stats video-learning-manager-gpu"
echo ""

# 10. 检查GPU使用情况
print_status "检查GPU使用情况..."
sleep 5
nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits

print_success "部署完成！系统已切换到GPU加速模式 🚀"