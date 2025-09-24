# 🚀 快速启动指南

## 一键完整启动

在服务器上执行以下步骤：

### 1. 获取代码和权限修复
```bash
# 如果没有项目目录，先克隆
git clone https://github.com/你的用户名/video-learning-manager.git
cd video-learning-manager

# 如果已有项目目录，修复权限并更新
sudo chown -R $(whoami):$(whoami) .
git config --global --add safe.directory $(pwd)
git pull origin main
```

### 2. 执行完整启动脚本
```bash
# 使脚本可执行
chmod +x startup.sh

# 一键启动（包含所有检查、下载、构建、验证）
./startup.sh
```

### 3. 启动过程说明

脚本会自动执行以下7个步骤：

1. **📋 环境检查** - 检查Docker、NVIDIA驱动、权限
2. **📥 代码更新** - 拉取最新代码
3. **📦 基础镜像** - 预下载CUDA、Nginx、Node.js镜像
4. **🔧 构建模型** - 构建应用镜像并下载medium/large-v3模型（**15-25分钟**）
5. **🤖 模型验证** - 验证两个模型是否正确安装
6. **🚀 启动服务** - 启动前后端服务
7. **✅ 最终验证** - 测试API和GPU状态

### 4. 完成后访问

- **前端界面**: http://your-server-ip
- **后端API**: http://your-server-ip:8000  
- **API文档**: http://your-server-ip:8000/docs

## 🎯 模型使用策略

- **📱 日常监控**: 自动使用 `medium` 模型
- **🎬 高质量**: 手动切换到 `large-v3` 模型（界面按钮）

## 🔧 常用维护命令

```bash
# 查看服务状态
docker-compose -f docker-compose.gpu.yml ps

# 查看日志
docker-compose -f docker-compose.gpu.yml logs -f

# 热更新（快速）
./deploy.sh hot

# 重启服务
docker-compose -f docker-compose.gpu.yml restart
```

## ❗ 注意事项

1. **首次启动较慢** - 需要下载约4GB的模型文件
2. **网络要求** - 确保服务器能访问Docker Hub和HuggingFace
3. **磁盘空间** - 建议至少50GB可用空间
4. **GPU内存** - RTX 3060 12GB足够运行两个模型

## 🔍 故障排除

如果启动失败，检查：

1. **权限问题**: `sudo chown -R $(whoami):$(whoami) .`
2. **网络问题**: 检查防火墙和代理设置
3. **磁盘空间**: `df -h` 检查可用空间
4. **GPU状态**: `nvidia-smi` 检查GPU

完成后，你的RTX 3060就可以全力进行视频转录了！🎉