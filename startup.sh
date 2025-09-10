#!/bin/bash

echo "🚀 启动视频学习管理器..."

# 检查依赖
check_dependency() {
    if ! command -v $1 &> /dev/null; then
        echo "❌ $1 未安装，请先安装"
        exit 1
    fi
}

echo "📋 检查系统依赖..."
check_dependency "python3"
check_dependency "node"
check_dependency "redis-server"
check_dependency "ffmpeg"

# 启动Redis
echo "🔄 启动Redis服务..."
sudo systemctl start redis-server

# 后端setup
echo "🐍 设置Python后端..."
cd backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt

# 创建数据目录
echo "📁 创建数据目录..."
sudo mkdir -p /var/video-learning-manager/{uploads,videos,audios,thumbnails}
sudo chown -R $USER:$USER /var/video-learning-manager

# 启动后端
echo "🔧 启动后端服务..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# 前端setup
echo "🎨 设置前端..."
cd ../frontend
npm install

# 启动前端
echo "🌐 启动前端服务..."
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ 服务启动完成！"
echo "🌐 前端地址: http://localhost:8080"
echo "🔧 后端API: http://localhost:8000"
echo "📚 API文档: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 等待中断信号
trap "echo '🛑 停止服务...'; kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait