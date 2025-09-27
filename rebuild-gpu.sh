#!/bin/bash

# GPU镜像重建和重启脚本
# 包含cuDNN 9.1修复

echo "🔄 停止现有容器..."
docker-compose -f docker-compose.gpu.yml down

echo "🧹 清理旧镜像（可选）..."
read -p "是否删除旧镜像以节省空间？[y/N]: " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker rmi video-learning-manager-gpu_video-learning-manager-gpu 2>/dev/null || true
    docker rmi video-learning-manager-frontend 2>/dev/null || true
fi

echo "🔨 构建新的GPU镜像（包含cuDNN 9.1）..."
docker-compose -f docker-compose.gpu.yml build --no-cache

echo "🚀 启动新容器..."
docker-compose -f docker-compose.gpu.yml up -d

echo "⏳ 等待服务启动..."
sleep 10

echo "🔍 检查服务状态..."
docker-compose -f docker-compose.gpu.yml ps

echo "🧪 测试GPU功能..."
sleep 5
curl -s -X GET "http://localhost:8000/api/local-videos/model-status" | python3 -m json.tool

echo "✅ 重建完成！现在可以添加更多视频进行测试"