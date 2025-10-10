# 视频学习管理器

智能视频字幕提取和学习管理系统，支持本地GPU加速转录和完整的Web界面。

## 功能特点

🚀 **GPU加速转录系统**
- 本地Whisper模型GPU加速（RTX 3060完美支持）
- CUDA 11.8优化，支持float16精度
- 完全离线运行，保护数据隐私

📱 **智能管理**
- 本地视频文件监控和自动处理
- 实时状态更新，无需手动刷新
- 明显的转录模式提醒（🌐 云端 / 💻 本地）

🎯 **性能优化**
- CPU占用从584%降至正常水平（17-18%）
- 并发控制，避免系统过载
- 智能队列管理

## 快速开始

### GPU加速部署（生产环境推荐）

**系统要求：**
- Debian/Ubuntu 服务器
- NVIDIA GPU（RTX 3060及以上）
- NVIDIA驱动 + nvidia-container-toolkit
- Docker + Docker Compose

1. **克隆项目**
```bash
git clone https://github.com/meitian2ke/video-learning-manager.git
cd video-learning-manager
```

2. **一键GPU部署**
```bash
chmod +x deploy.sh
./deploy.sh
```

3. **访问应用**
- 🌐 前端界面: http://your-server-ip (端口80)
- 🔧 后端API: http://your-server-ip:8000
- 📚 API文档: http://your-server-ip:8000/docs
- 📊 GPU监控: http://your-server-ip/api/gpu/status

### 📋 更新方式 - 三种选择

```bash
# 🔥 热更新（推荐，2-3分钟）- 适用于代码修改
./deploy.sh hot

# 📦 常规更新（5-10分钟）- 适用于新功能添加  
./deploy.sh update

# 🔧 完全重构（15-30分钟）- 适用于重大版本更新
./deploy.sh rebuild
```

> **💡 推荐**: 日常使用热更新模式，避免网络构建问题

### CPU版本部署（开发环境）

```bash
docker-compose up -d
```

访问: http://localhost:8000

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

### GPU加速配置
```env
TRANSCRIPTION_MODE=local  # 本地模式
WHISPER_DEVICE=cuda       # GPU加速
WHISPER_COMPUTE_TYPE=float16  # 精度优化
WHISPER_MODEL=base        # 模型大小 (tiny/base/small/medium/large)
MAX_CONCURRENT_TRANSCRIPTIONS=3  # 并发控制
FORCE_CPU_MODE=false      # 禁用CPU强制模式
AUTO_GPU_DETECTION=true   # 自动GPU检测
```

### 开机自启动
部署脚本自动配置systemd服务：
```bash
sudo systemctl status video-learning-gpu  # 查看状态
sudo systemctl start video-learning-gpu   # 手动启动
sudo systemctl stop video-learning-gpu    # 手动停止
```

## 系统要求

### GPU生产环境
- **硬件**: NVIDIA GPU (RTX 3060及以上)，建议150GB+磁盘空间
- **系统**: Debian 11/12 或 Ubuntu 22.04 LTS
- **软件**: NVIDIA驱动，Docker 20.0+，Docker Compose，nvidia-container-toolkit

### 开发环境
- **软件**: Python 3.11+，Node.js 18+，FFmpeg

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