#!/bin/bash

# 修复Whisper模型和配置问题

set -e

echo "🔧 修复Whisper模型和GPU配置..."

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

# 1. 停止现有服务
print_status "停止现有服务..."
docker-compose -f docker-compose.gpu.yml down

# 2. 创建模型下载脚本
print_status "创建Whisper模型预下载脚本..."
cat > download_whisper_model.py << 'EOF'
#!/usr/bin/env python3
import os
import sys

def download_whisper_model():
    """预下载Whisper模型"""
    print("🔍 开始下载Whisper模型...")
    
    try:
        # 设置HuggingFace缓存目录
        os.environ['HF_HOME'] = '/root/.cache/huggingface'
        os.environ['TRANSFORMERS_CACHE'] = '/root/.cache/huggingface'
        
        # 检查是否有GPU
        try:
            import torch
            gpu_available = torch.cuda.is_available()
            if gpu_available:
                device = "cuda"
                compute_type = "float16"
                print(f"✅ GPU可用: {torch.cuda.get_device_name(0)}")
            else:
                device = "cpu" 
                compute_type = "int8"
                print("⚠️ GPU不可用，使用CPU模式")
        except ImportError:
            device = "cpu"
            compute_type = "int8"
            print("⚠️ PyTorch未找到，使用CPU模式")
        
        print(f"📥 下载Whisper base模型到 {device}...")
        
        # 创建缓存目录
        cache_dir = "/root/.cache/huggingface/hub"
        os.makedirs(cache_dir, exist_ok=True)
        
        # 导入faster_whisper并下载模型
        from faster_whisper import WhisperModel
        
        # 下载模型（这会自动下载到HuggingFace缓存）
        print("📥 正在下载模型文件...")
        model = WhisperModel("base", device=device, compute_type=compute_type, download_root=cache_dir)
        print("✅ 模型下载完成!")
        
        # 简单测试（不需要实际音频文件）
        print("🧪 模型加载测试完成")
        
        # 检查模型文件是否存在
        model_path = "/root/.cache/huggingface/hub/models--guillaumekln--faster-whisper-base"
        if os.path.exists(model_path):
            print(f"✅ 模型文件确认存在: {model_path}")
        else:
            print(f"⚠️ 模型路径不存在: {model_path}")
            # 列出实际的缓存目录内容
            print("📂 实际缓存目录内容:")
            if os.path.exists("/root/.cache/huggingface/hub"):
                for item in os.listdir("/root/.cache/huggingface/hub"):
                    print(f"  - {item}")
        
        return True
        
    except Exception as e:
        print(f"❌ 模型下载失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = download_whisper_model()
    exit(0 if success else 1)
EOF

# 3. 更新Dockerfile预下载模型
print_status "更新GPU Dockerfile添加模型预下载..."

# 备份原文件
cp Dockerfile.gpu Dockerfile.gpu.backup

# 在Dockerfile中添加模型下载步骤
cat > Dockerfile.gpu << 'EOF'
# GPU优化版Dockerfile - 专为生产环境设计
FROM nvidia/cuda:11.8.0-devel-ubuntu22.04

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

# 设置HuggingFace缓存目录
ENV HF_HOME=/root/.cache/huggingface
ENV TRANSFORMERS_CACHE=/root/.cache/huggingface
ENV HF_HUB_CACHE=/root/.cache/huggingface/hub

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3-pip \
    ffmpeg \
    git \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 升级pip（直接使用python3.11）
RUN python3.11 -m pip install --upgrade pip

# 复制requirements文件
COPY requirements.txt .

# 配置pip使用国内镜像源（大幅提升下载速度）
RUN python3.11 -m pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple/ && \
    python3.11 -m pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn

# 安装PyTorch GPU版本（使用国内源 + CUDA 11.8）
RUN python3.11 -m pip install torch torchvision torchaudio \
    -i https://pypi.tuna.tsinghua.edu.cn/simple/ \
    --extra-index-url https://download.pytorch.org/whl/cu118

# 安装其他依赖
RUN python3.11 -m pip install --no-cache-dir -r requirements.txt

# 创建缓存目录
RUN mkdir -p /root/.cache/huggingface/hub

# 复制模型下载脚本
COPY download_whisper_model.py .

# 预下载Whisper模型（关键步骤！）
RUN echo "🔥 开始预下载Whisper模型..." && \
    python3.11 download_whisper_model.py && \
    echo "✅ Whisper模型预下载完成" && \
    ls -la /root/.cache/huggingface/hub/ || echo "模型目录检查失败"

# 复制应用代码
COPY backend/ ./backend/
COPY local-videos/ ./local-videos/

# 创建必要的目录
RUN mkdir -p /app/data/uploads \
             /app/data/videos \
             /app/data/audios \
             /app/data/thumbnails \
             /app/data/local-videos \
             /app/logs

# 设置权限
RUN chmod -R 755 /app

# 环境变量
ENV PYTHONPATH=/app/backend
ENV ENVIRONMENT=production
ENV WHISPER_DEVICE=cuda
ENV WHISPER_COMPUTE_TYPE=float16
ENV WHISPER_MODEL=base
ENV MAX_CONCURRENT_TRANSCRIPTIONS=3
ENV FORCE_CPU_MODE=false
ENV TRANSCRIPTION_MODE=local

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python3.11", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
EOF

print_success "Dockerfile已更新，添加了模型预下载"

# 4. 检查配置文件
print_status "检查后端配置..."
if grep -q "TRANSCRIPTION_MODE.*openai" backend/app/core/config.py; then
    print_warning "发现配置中还有OpenAI模式，正在修改为本地模式..."
    
    # 备份配置文件
    cp backend/app/core/config.py backend/app/core/config.py.backup
    
    # 修改配置为本地模式
    sed -i 's/TRANSCRIPTION_MODE.*=.*"openai"/TRANSCRIPTION_MODE: str = "local"/' backend/app/core/config.py
    sed -i 's/TRANSCRIPTION_MODE.*=.*"auto"/TRANSCRIPTION_MODE: str = "local"/' backend/app/core/config.py
    
    print_success "配置已修改为本地模式"
else
    print_success "配置已经是本地模式"
fi

# 5. 重新构建镜像
print_status "重新构建GPU镜像（包含模型预下载）..."
docker-compose -f docker-compose.gpu.yml build --no-cache

# 6. 启动服务
print_status "启动修复后的服务..."
docker-compose -f docker-compose.gpu.yml up -d

# 7. 等待服务启动
print_status "等待服务启动..."
sleep 15

# 8. 检查服务状态
if curl -s http://localhost/health > /dev/null 2>&1; then
    print_success "✅ 服务启动成功!"
    echo ""
    echo "📊 服务信息:"
    echo "  - 前端界面: http://$(hostname -I | awk '{print $1}')"
    echo "  - GPU监控: http://$(hostname -I | awk '{print $1}')/api/gpu/status"
    echo ""
    echo "🔧 故障排除:"
    echo "  - 查看日志: docker-compose -f docker-compose.gpu.yml logs -f"
    echo "  - 检查GPU: nvidia-smi"
    echo "  - 测试转录: 上传一个小视频文件"
else
    print_error "❌ 服务启动失败!"
    echo ""
    echo "📋 检查步骤:"
    echo "1. 查看容器状态: docker-compose -f docker-compose.gpu.yml ps"
    echo "2. 查看后端日志: docker logs video-learning-manager-gpu"
    echo "3. 查看前端日志: docker logs video-learning-frontend"
fi

print_success "修复脚本执行完成!"