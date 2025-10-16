#!/bin/bash
set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🚀 自动提交脚本${NC}"

# 检查是否有修改
if [[ -z $(git status --porcelain) ]]; then
    echo -e "${YELLOW}没有文件需要提交${NC}"
    exit 0
fi

# 显示将要提交的文件
echo -e "${YELLOW}以下文件将被提交:${NC}"
git status --short

# 添加所有修改的文件（包括新文件）
git add -A

# 获取提交信息
if [ "$1" ]; then
    commit_message="$1"
else
    echo ""
    read -p "请输入提交信息: " commit_message
    if [ -z "$commit_message" ]; then
        commit_message="自动提交 $(date '+%Y-%m-%d %H:%M:%S')"
    fi
fi

# 提交
echo -e "${GREEN}正在提交...${NC}"
git commit -m "$commit_message

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# 推送
echo -e "${GREEN}正在推送到GitHub...${NC}"
git push origin main

echo -e "${GREEN}✅ 提交完成！${NC}"
