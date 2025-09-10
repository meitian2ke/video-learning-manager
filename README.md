# 视频学习管理器

一个智能的视频学习内容管理工具，支持从微信、抖音、B站等平台提取视频字幕，并提供学习进度管理功能。

## 功能特点

- 🎥 **多平台支持**: 支持微信、抖音、B站、YouTube等主流视频平台
- 🤖 **AI字幕提取**: 使用 Faster-Whisper 进行高精度中文字幕识别
- 📝 **智能内容整理**: 自动生成摘要、提取关键词标签
- 📊 **学习进度管理**: 跟踪学习状态、记录学习笔记
- 🏷️ **分类管理**: 支持视频分类和标签管理
- 📈 **统计分析**: 学习进度统计和可视化

## 技术架构

### 后端技术栈
- **Python 3.11** + **FastAPI** - API服务
- **SQLite** - 数据存储
- **Faster-Whisper** - AI字幕识别
- **yt-dlp** - 视频下载
- **FFmpeg** - 音频处理
- **Redis** + **Celery** - 异步任务处理

### 前端技术栈
- **Vue.js 3** - 前端框架
- **Element Plus** - UI组件库
- **Pinia** - 状态管理
- **TypeScript** - 类型支持

## 快速开始

### 1. 环境要求
- Python 3.11+
- Node.js 18+
- Redis
- FFmpeg
- Docker (可选)

### 2. 使用 Docker 部署 (推荐)

```bash
# 克隆项目
git clone <repository-url>
cd video-learning-manager

# 启动服务
docker-compose up -d

# 访问应用
open http://localhost
```

### 3. 手动部署

#### 后端部署
```bash
cd backend

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### 前端部署
```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build
```

## 使用说明

### 1. 添加视频
1. 访问首页，输入视频链接
2. 选择优先级和分类（可选）
3. 点击"添加视频"，系统会自动：
   - 下载视频
   - 提取音频
   - 生成字幕
   - 创建学习记录

### 2. 管理视频
1. 进入"视频列表"页面
2. 查看所有视频的处理状态和学习进度
3. 可以：
   - 查看视频详情和字幕内容
   - 编辑学习笔记
   - 更新学习状态
   - 标记实践完成情况

### 3. 学习管理
- **学习状态**: 待学习 → 学习中 → 已完成
- **实践状态**: 未开始 → 计划中 → 实施中 → 已完成
- **笔记记录**: 支持富文本笔记和代码仓库链接
- **进度统计**: 可视化学习进度和完成率

## 配置说明

### 环境变量
创建 `backend/.env` 文件：
```bash
# 数据库配置
DATABASE_URL=sqlite:///./video_learning.db

# Redis配置
REDIS_URL=redis://localhost:6379/0

# 文件存储路径
UPLOAD_DIR=/var/video-learning-manager/uploads
VIDEO_DIR=/var/video-learning-manager/videos

# Whisper配置
WHISPER_MODEL=medium
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8

# 安全配置
SECRET_KEY=your-secret-key-here
```

## API 文档

启动后端服务后，访问 http://localhost:8000/docs 查看完整的 API 文档。

## 目录结构

```
video-learning-manager/
├── backend/                 # 后端代码
│   ├── app/
│   │   ├── api/            # API路由
│   │   ├── core/           # 核心配置
│   │   ├── models/         # 数据模型
│   │   └── services/       # 业务服务
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                # 前端代码
│   ├── src/
│   │   ├── views/          # 页面组件
│   │   ├── stores/         # 状态管理
│   │   └── router/         # 路由配置
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml       # Docker编排文件
├── nginx.conf              # Nginx配置
└── README.md
```

## 常见问题

### Q: 视频下载失败怎么办？
A: 检查网络连接，某些平台可能需要特殊处理，可以尝试更新 yt-dlp 版本。

### Q: 字幕识别准确率不高怎么办？
A: 可以尝试使用更大的模型（large），或者手动编辑清理后的文本。

### Q: 如何备份数据？
A: 定期备份 SQLite 数据库文件和视频文件目录。

## 贡献指南

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License