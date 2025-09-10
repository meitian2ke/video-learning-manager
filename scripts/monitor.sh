#!/bin/bash

# 服务监控脚本

PROJECT_DIR="/opt/video-learning-manager"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}📊 视频学习管理器 - 服务监控${NC}"
echo "=========================================="

# 检查Docker服务
echo -e "\n${YELLOW}🐳 Docker状态:${NC}"
if systemctl is-active --quiet docker; then
    echo -e "${GREEN}✅ Docker服务运行中${NC}"
else
    echo -e "${RED}❌ Docker服务未运行${NC}"
fi

# 检查容器状态
echo -e "\n${YELLOW}📦 容器状态:${NC}"
cd $PROJECT_DIR 2>/dev/null || { echo "项目目录不存在"; exit 1; }

containers=("video-manager-backend" "video-manager-frontend" "video-manager-redis" "video-manager-nginx")

for container in "${containers[@]}"; do
    if docker ps --format "table {{.Names}}" | grep -q "^$container$"; then
        status=$(docker inspect --format='{{.State.Health.Status}}' $container 2>/dev/null || echo "no-healthcheck")
        if [ "$status" = "healthy" ] || [ "$status" = "no-healthcheck" ]; then
            echo -e "${GREEN}✅ $container${NC}"
        else
            echo -e "${YELLOW}⚠️  $container (健康检查: $status)${NC}"
        fi
    else
        echo -e "${RED}❌ $container 未运行${NC}"
    fi
done

# 检查网络连接
echo -e "\n${YELLOW}🌐 网络连接:${NC}"

# 后端API
if curl -f http://localhost:8000/health >/dev/null 2>&1; then
    echo -e "${GREEN}✅ 后端API (8000)${NC}"
else
    echo -e "${RED}❌ 后端API (8000)${NC}"
fi

# 前端
if curl -f http://localhost >/dev/null 2>&1; then
    echo -e "${GREEN}✅ 前端服务 (80)${NC}"
else
    echo -e "${RED}❌ 前端服务 (80)${NC}"
fi

# Redis
if docker exec video-manager-redis redis-cli ping >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis服务${NC}"
else
    echo -e "${RED}❌ Redis服务${NC}"
fi

# 系统资源
echo -e "\n${YELLOW}💻 系统资源:${NC}"

# CPU使用率
cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
echo -e "CPU使用率: ${cpu_usage}%"

# 内存使用率
memory_info=$(free | grep Mem)
total_mem=$(echo $memory_info | awk '{print $2}')
used_mem=$(echo $memory_info | awk '{print $3}')
memory_usage=$((used_mem * 100 / total_mem))
echo -e "内存使用率: ${memory_usage}%"

# 磁盘使用率
disk_usage=$(df -h / | awk 'NR==2 {print $5}' | cut -d'%' -f1)
echo -e "磁盘使用率: ${disk_usage}%"

# Docker资源使用
echo -e "\n${YELLOW}🐋 Docker资源:${NC}"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null || echo "无法获取Docker统计信息"

# 最近日志
echo -e "\n${YELLOW}📋 最近日志 (最后10行):${NC}"
echo "后端日志:"
docker logs video-manager-backend --tail 5 2>/dev/null | head -5 || echo "无法获取后端日志"

echo -e "\nNginx日志:"
docker logs video-manager-nginx --tail 5 2>/dev/null | head -5 || echo "无法获取Nginx日志"

# 数据库大小
echo -e "\n${YELLOW}💾 数据库信息:${NC}"
if [ -f "$PROJECT_DIR/data/video_learning.db" ]; then
    db_size=$(du -h "$PROJECT_DIR/data/video_learning.db" | cut -f1)
    echo -e "数据库大小: ${db_size}"
else
    echo -e "${RED}❌ 数据库文件不存在${NC}"
fi

# 存储空间
echo -e "\n${YELLOW}📁 存储使用:${NC}"
if [ -d "$PROJECT_DIR/videos" ]; then
    videos_size=$(du -sh "$PROJECT_DIR/videos" 2>/dev/null | cut -f1 || echo "0")
    echo -e "视频文件: ${videos_size}"
fi

if [ -d "$PROJECT_DIR/audios" ]; then
    audios_size=$(du -sh "$PROJECT_DIR/audios" 2>/dev/null | cut -f1 || echo "0")
    echo -e "音频文件: ${audios_size}"
fi

echo -e "\n${BLUE}=========================================="
echo -e "监控完成 - $(date)${NC}"
echo ""
echo "💡 有用的命令:"
echo "  实时日志: docker-compose -f $PROJECT_DIR/docker-compose.prod.yml logs -f"
echo "  重启服务: docker-compose -f $PROJECT_DIR/docker-compose.prod.yml restart"
echo "  进入容器: docker exec -it video-manager-backend bash"