# 多阶段构建：前端构建
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# 主镜像：Python后端 + 前端静态文件
FROM python:3.11-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制Python依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY backend/ ./backend/

# 复制前端构建结果
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# 创建必要的目录
RUN mkdir -p /app/data/uploads /app/data/videos /app/data/audios /app/data/thumbnails /app/data/local-videos

# 设置环境变量
ENV PYTHONPATH=/app/backend
ENV UPLOAD_DIR=/app/data/uploads
ENV VIDEO_DIR=/app/data/videos
ENV AUDIO_DIR=/app/data/audios
ENV THUMBNAIL_DIR=/app/data/thumbnails
ENV LOCAL_VIDEO_DIR=/app/data/local-videos

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]