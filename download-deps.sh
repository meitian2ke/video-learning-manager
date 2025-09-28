#!/bin/bash

# 预下载所有依赖，避免每次构建都重新下载
# 这样19GB镜像构建会快很多

echo "📁 创建downloads目录..."
mkdir -p downloads

cd downloads

echo "🔥 1. 下载cuDNN 9.1 (840MB)..."
if [ ! -f "cudnn-linux-x86_64-9.1.0.70_cuda11-archive.tar.xz" ]; then
    wget https://developer.download.nvidia.com/compute/cudnn/redist/cudnn/linux-x86_64/cudnn-linux-x86_64-9.1.0.70_cuda11-archive.tar.xz
else
    echo "✅ cuDNN已存在，跳过"
fi

echo "🐍 2. 下载PyTorch wheels (约4GB)..."
mkdir -p torch_wheels
cd torch_wheels

# PyTorch GPU版本wheels (强制CUDA 11.8版本，避免CUDA 12冲突)
if [ ! -f "torch-*+cu118*.whl" ]; then
    echo "正在下载PyTorch CUDA 11.8版本..."
    python3 -m pip download torch==2.1.0+cu118 torchvision==0.16.0+cu118 torchaudio==2.1.0+cu118 \
        --extra-index-url https://download.pytorch.org/whl/cu118 --dest . --no-deps
    
    # 验证下载的确实是CUDA 11.8版本
    if ls *cu12*.whl 1> /dev/null 2>&1; then
        echo "❌ 错误：下载了CUDA 12版本，删除重试"
        rm -f *cu12*.whl
        exit 1
    fi
else
    echo "✅ PyTorch CUDA 11.8 wheels已存在，跳过"
fi

cd ..

echo "🔧 3. 下载Python依赖wheels..."
mkdir -p python_wheels
cd python_wheels

if [ ! -f "faster_whisper-*.whl" ]; then
    python3 -m pip download -r ../../requirements.txt --dest .
    python3 -m pip download faster-whisper==0.9.0 transformers huggingface-hub --dest .
else
    echo "✅ Python wheels已存在，跳过"
fi

cd ..

echo "📊 下载完成，查看文件大小："
du -sh *

echo "🎉 所有依赖已预下载完成！现在构建镜像会快很多。"