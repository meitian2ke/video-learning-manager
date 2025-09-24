#!/bin/bash

# 🔧 修复Git权限问题
# 解决文件所有权和权限不足的问题

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "🔧 修复Git权限问题"
echo "==============================================="

# 获取当前用户
CURRENT_USER=$(whoami)
print_status "当前用户: $CURRENT_USER"

# 获取项目目录
PROJECT_DIR=$(pwd)
print_status "项目目录: $PROJECT_DIR"

# 修复文件所有权
print_status "修复文件所有权..."
sudo chown -R $CURRENT_USER:$CURRENT_USER $PROJECT_DIR

# 修复.git目录权限
print_status "修复.git目录权限..."
sudo chmod -R u+rwx .git/

# 添加安全目录
print_status "添加Git安全目录..."
git config --global --add safe.directory $PROJECT_DIR

# 验证修复结果
print_status "验证修复结果..."
if git status >/dev/null 2>&1; then
    print_success "✅ Git权限修复成功！"
    
    # 尝试拉取代码
    print_status "尝试拉取最新代码..."
    if git pull origin main; then
        print_success "✅ 代码拉取成功！"
    else
        print_warning "⚠️ 代码拉取失败，可能需要手动解决冲突"
    fi
else
    print_error "❌ Git权限修复失败"
    exit 1
fi

print_success "🎯 权限修复完成！现在可以正常使用Git命令了。"