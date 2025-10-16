#!/bin/bash

# 稳妥的Docker构建脚本 - 支持预下载wheels作为备用
set -e

echo "🏗️ 开始稳妥的Docker构建流程..."

# 步骤1: 预下载wheels作为备用（可选）
echo ""
echo "📦 步骤1: 预下载wheels作为备用..."
if [[ "$1" == "--download-wheels" ]] || [[ "$1" == "-d" ]]; then
    echo "🚀 执行预下载wheels..."
    ./download-wheels.sh
    
    
    # 如果下载成功，启用COPY指令
    if [ -d "models/wheels" ] && [ "$(ls -A models/wheels)" ]; then
        echo "✅ 发现本地wheels，启用Docker中的COPY指令..."
        sed -i.bak 's/^# COPY models\/wheels/COPY models\/wheels/' Dockerfile.gpu
    fi
else
    echo "⏭️ 跳过预下载，使用在线安装..."
fi

# 步骤2: 构建Docker镜像
echo ""
echo "🐳 步骤2: 构建Docker镜像..."
echo "💡 使用多层级回退策略确保构建成功..."

# 清理Docker缓存（可选）
if [[ "$2" == "--no-cache" ]] || [[ "$1" == "--no-cache" ]]; then
    echo "🧹 清理Docker缓存..."
    docker system prune -f
    BUILD_ARGS="--no-cache"
else
    BUILD_ARGS=""
fi

# 执行构建
docker-compose -f docker-compose.gpu.yml build $BUILD_ARGS

# 步骤3: 恢复Dockerfile（如果修改过）
if [ -f "Dockerfile.gpu.bak" ]; then
    echo "🔄 恢复Dockerfile原状..."
    mv Dockerfile.gpu.bak Dockerfile.gpu
fi

echo ""
echo "✅ 构建完成！"
echo ""
echo "💡 使用说明:"
echo "  ./build-with-backup.sh           # 纯在线安装"
echo "  ./build-with-backup.sh -d        # 预下载wheels作为备用"
echo "  ./build-with-backup.sh --no-cache # 清理缓存重新构建"
echo ""
echo "🚀 启动服务: ./run.sh start"