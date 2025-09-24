# 🚀 部署和更新指南

## 快速部署

### 首次部署
```bash
git clone https://github.com/meitian2ke/video-learning-manager.git
cd video-learning-manager
chmod +x deploy.sh
./deploy.sh
```

### 日常更新 - 三种方式

#### 1. 🔥 热更新（推荐，2-3分钟）
```bash
./deploy.sh hot
```
- **适用场景**: 代码修改、配置调整
- **优点**: 最快，避免网络构建问题
- **过程**: 拉取代码 → 替换文件 → 重启容器

#### 2. 📦 常规更新（5-10分钟）
```bash
./deploy.sh update
```
- **适用场景**: 依赖更新、新功能添加
- **优点**: 使用缓存，相对较快
- **过程**: 拉取代码 → 停止 → 构建（使用缓存）→ 启动

#### 3. 🔧 完全重构（15-30分钟）
```bash
./deploy.sh rebuild
```
- **适用场景**: 重大版本更新、解决构建问题
- **优点**: 彻底清理，确保环境一致
- **过程**: 拉取代码 → 清理缓存 → 完全重构 → 启动

## 系统要求

### GPU生产环境
- **硬件**: NVIDIA GPU (RTX 3060及以上)，建议150GB+磁盘空间
- **系统**: Debian 11/12 或 Ubuntu 22.04 LTS  
- **软件**: NVIDIA驱动，Docker 20.0+，Docker Compose，nvidia-container-toolkit

### 开发环境
- **软件**: Python 3.11+，Node.js 18+，FFmpeg

## 服务访问

部署成功后可以访问：
- **前端界面**: http://your-server-ip (端口80)
- **后端API**: http://your-server-ip:8000
- **API文档**: http://your-server-ip:8000/docs
- **GPU监控**: http://your-server-ip/api/gpu/status
- **处理状态**: http://your-server-ip:8000/api/local-videos/processing-status

## 常用命令

```bash
# 查看服务状态
docker-compose -f docker-compose.gpu.yml ps

# 查看日志
docker-compose -f docker-compose.gpu.yml logs -f

# 重启服务
docker-compose -f docker-compose.gpu.yml restart

# 停止服务
docker-compose -f docker-compose.gpu.yml down

# 检查GPU状态
nvidia-smi
```

## 故障排除

### 常见问题
1. **容器启动失败**: 检查日志 `docker logs video-learning-manager-gpu`
2. **GPU不工作**: 检查nvidia-container-toolkit安装
3. **网络构建失败**: 使用热更新模式 `./deploy.sh hot`
4. **视频处理失败**: 检查Whisper模型是否下载成功

### 服务管理
```bash
# 开机自启动
sudo systemctl enable video-learning-gpu
sudo systemctl start video-learning-gpu

# 检查服务状态
sudo systemctl status video-learning-gpu
```