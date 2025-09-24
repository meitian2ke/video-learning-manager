#!/bin/bash

# 🤖 Whisper模型下载脚本
# 确保所有必要的模型都已下载

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

echo "🤖 Whisper模型下载脚本"
echo "==============================================="

# 检查容器是否运行
if ! docker ps | grep -q video-learning-manager-gpu; then
    print_error "后端容器未运行！请先启动服务"
    print_status "运行: docker-compose -f docker-compose.gpu.yml up -d"
    exit 1
fi

print_success "找到运行中的容器"

# 检查模型是否已存在
print_status "检查现有模型..."
if docker exec video-learning-manager-gpu test -d /root/.cache/huggingface/hub/models--guillaumekln--faster-whisper-base; then
    print_success "✅ Whisper base模型已存在"
    
    # 显示模型信息
    model_size=$(docker exec video-learning-manager-gpu du -sh /root/.cache/huggingface/hub/models--guillaumekln--faster-whisper-base | cut -f1)
    print_status "模型大小: $model_size"
    
    # 测试模型是否可用
    print_status "测试模型是否可用..."
    if docker exec video-learning-manager-gpu python3.11 -c "
from faster_whisper import WhisperModel
try:
    model = WhisperModel('base', device='cuda', compute_type='float16')
    print('✅ 模型加载成功，可以正常使用')
except Exception as e:
    print(f'❌ 模型加载失败: {e}')
    exit(1)
" 2>/dev/null; then
        print_success "🚀 模型测试通过，可以开始处理视频了！"
        exit 0
    else
        print_warning "模型存在但无法正常加载，重新下载..."
    fi
else
    print_warning "❌ 模型未找到，开始下载..."
fi

# 下载模型
print_status "开始下载Whisper模型（这可能需要几分钟）..."

# 创建下载脚本
cat > /tmp/download_whisper.py << 'EOF'
import os
import sys
from faster_whisper import WhisperModel

def download_model():
    """下载Whisper模型"""
    try:
        print("🔍 设置缓存目录...")
        os.environ['HF_HOME'] = '/root/.cache/huggingface'
        os.environ['TRANSFORMERS_CACHE'] = '/root/.cache/huggingface'
        
        print("📥 开始下载Whisper base模型...")
        print("这可能需要几分钟，请耐心等待...")
        
        # 下载模型
        model = WhisperModel('base', device='cuda', compute_type='float16')
        
        print("✅ 模型下载完成！")
        
        # 验证模型
        print("🧪 验证模型...")
        model_path = '/root/.cache/huggingface/hub/models--guillaumekln--faster-whisper-base'
        if os.path.exists(model_path):
            print(f"✅ 模型文件确认存在: {model_path}")
            
            # 显示模型文件
            for root, dirs, files in os.walk(model_path):
                for file in files[:5]:  # 只显示前5个文件
                    print(f"  - {file}")
            
            return True
        else:
            print(f"❌ 模型路径不存在: {model_path}")
            return False
            
    except Exception as e:
        print(f"❌ 下载失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = download_model()
    sys.exit(0 if success else 1)
EOF

# 复制脚本到容器并执行
docker cp /tmp/download_whisper.py video-learning-manager-gpu:/tmp/

print_status "在容器内执行模型下载..."
if docker exec video-learning-manager-gpu python3.11 /tmp/download_whisper.py; then
    print_success "🎉 Whisper模型下载完成！"
    
    # 显示最终状态
    echo ""
    print_status "📊 模型状态总结:"
    docker exec video-learning-manager-gpu ls -la /root/.cache/huggingface/hub/ | grep whisper || echo "  无whisper相关文件"
    
    # 最终测试
    print_status "🧪 最终功能测试..."
    if docker exec video-learning-manager-gpu python3.11 -c "
from faster_whisper import WhisperModel
model = WhisperModel('base', device='cuda', compute_type='float16')
print('🚀 模型可以正常使用，GPU转录功能已就绪！')
" 2>/dev/null; then
        print_success "✅ 所有测试通过，可以开始处理视频了！"
        echo ""
        print_status "💡 提示: 现在可以在Web界面上传视频进行GPU加速转录"
    else
        print_error "❌ 最终测试失败，请检查GPU环境"
        exit 1
    fi
else
    print_error "❌ 模型下载失败"
    echo ""
    print_status "🔧 故障排除:"
    echo "1. 检查网络连接"
    echo "2. 检查容器内存是否充足"  
    echo "3. 检查GPU驱动是否正常"
    echo "4. 重启容器: docker restart video-learning-manager-gpu"
    exit 1
fi

# 清理临时文件
rm -f /tmp/download_whisper.py
docker exec video-learning-manager-gpu rm -f /tmp/download_whisper.py

echo ""
print_success "🎯 模型下载和验证完成！系统已准备就绪。"