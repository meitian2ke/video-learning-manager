#!/bin/bash

# 预下载wheels和依赖到本地，作为备用方案
set -e

echo "📦 开始下载Python包到本地..."

# 创建必要目录
mkdir -p models/wheels

# 下载最新版本的faster-whisper及其依赖
echo "📥 下载faster-whisper>=1.0.3及其依赖..."
python3 -m pip download \
    "faster-whisper>=1.0.3" \
    "transformers>=4.20.0" \
    "huggingface-hub>=0.15.0" \
    --dest models/wheels \
    --no-deps

# 下载兼容的PyAV版本作为备用
echo "📥 下载兼容的PyAV版本作为备用..."
python3 -m pip download \
    "av>=9.2.0,<11.0.0" \
    --dest models/wheels \
    --prefer-binary

echo "✅ 所有包已下载到 models/wheels/"
echo "📂 可用文件:"
ls -la models/wheels/

echo ""
echo "💡 使用说明:"
echo "  - 这些wheel文件将在Docker构建时作为备用安装源"
echo "  - 如果在线安装失败，会自动使用本地wheel文件"
echo "  - 确保在构建Docker镜像前运行此脚本"