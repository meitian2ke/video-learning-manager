# 视频学习管理器

智能视频字幕提取和学习管理系统，支持双模式AI转录（云端优先，本地备用）。

## 功能特点

🌐 **双模式转录系统**
- OpenAI云端API转录（主模式，低CPU占用）
- 本地Whisper模型转录（备用模式，支持离线）
- 自动降级机制，确保服务可靠性

📱 **智能管理**
- 本地视频文件监控和自动处理
- 实时状态更新，无需手动刷新
- 明显的转录模式提醒（🌐 云端 / 💻 本地）

🎯 **性能优化**
- CPU占用从584%降至正常水平（17-18%）
- 并发控制，避免系统过载
- 智能队列管理

## 快速开始

### 使用Docker部署（推荐）

1. **克隆项目**
```bash
git clone https://github.com/meitian2ke/video-learning-manager.git
cd video-learning-manager
```

2. **配置环境变量（可选）**
```bash
# 创建 .env 文件
cp .env.example .env
# 编辑 .env 文件，设置你的 OpenAI API Key
```

3. **启动服务**
```bash
docker-compose up -d
```

4. **访问应用**
- 前端界面: http://localhost:8000
- API文档: http://localhost:8000/docs

### 手动部署

#### 后端启动
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r ../requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 前端启动
```bash
cd frontend
npm install
npm run dev
```

## 配置说明

### 转录模式
- `TRANSCRIPTION_MODE=openai`: 使用OpenAI云端API（推荐）
- `TRANSCRIPTION_MODE=local`: 使用本地Whisper模型

### OpenAI API配置
```env
OPENAI_API_KEY=your-api-key-here
OPENAI_BASE_URL=https://api.openai.com  # 或第三方代理
```

### 本地模型配置
```env
WHISPER_MODEL=tiny  # tiny, base, small, medium, large
WHISPER_DEVICE=cpu  # cpu, cuda
WHISPER_COMPUTE_TYPE=int8
```

## 系统要求

- **Docker**: Docker 20.0+ 和 Docker Compose 1.28+
- **手动部署**: Python 3.11+, Node.js 18+, FFmpeg

## 使用说明

1. **添加视频**: 支持URL导入或本地文件监控
2. **自动转录**: 系统自动检测新视频并进行转录
3. **查看结果**: 实时查看转录进度和结果
4. **模式切换**: 可通过API动态切换转录模式

## API文档

启动服务后访问 http://localhost:8000/docs 查看完整API文档。

主要端点:
- `GET /api/system/config` - 获取系统配置
- `POST /api/system/config/transcription` - 切换转录模式
- `GET /api/local-videos/list` - 获取本地视频列表
- `POST /api/local-videos/process/{video_name}` - 处理指定视频

## 开发说明

### 项目结构
```
├── backend/          # Python FastAPI后端
├── frontend/         # Vue.js前端
├── local-videos/     # 本地视频存储目录
├── data/            # 数据持久化目录
├── Dockerfile       # Docker镜像构建
└── docker-compose.yml  # Docker编排文件
```

### 开发计划

**第一阶段 ✅ 已完成**
- 双模式AI转录系统
- 本地视频文件管理
- 实时状态更新

**第二阶段（规划中）**
- 智能学习功能
- 视频分类管理
- 学习进度追踪
- 内容分析增强

## 故障排除

### 常见问题

1. **CPU占用过高**
   - 确保使用OpenAI模式：`TRANSCRIPTION_MODE=openai`
   - 检查并发数设置：`MAX_CONCURRENT_TRANSCRIPTIONS=1`

2. **转录失败**
   - 检查OpenAI API Key是否正确
   - 确认网络连接正常
   - 查看日志中的错误信息

3. **Docker构建失败**
   - 确保Docker版本符合要求
   - 检查网络连接，某些依赖可能需要科学上网

## 贡献指南

欢迎提交Issue和Pull Request！

## 许可证

MIT License