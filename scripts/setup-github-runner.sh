#!/bin/bash

# GitHub Actions Self-hosted Runner 安装脚本
# 在你的Debian服务器上运行此脚本

set -e

echo "🚀 设置GitHub Actions Self-hosted Runner..."

# 检查是否为root用户
if [ "$EUID" -eq 0 ]; then
    echo "❌ 请不要以root用户运行此脚本"
    exit 1
fi

# 获取用户输入
read -p "请输入你的GitHub用户名: " GITHUB_USERNAME
read -p "请输入仓库名称 (video-learning-manager): " REPO_NAME
REPO_NAME=${REPO_NAME:-video-learning-manager}

echo "📝 GitHub仓库: $GITHUB_USERNAME/$REPO_NAME"

# 创建runner目录
RUNNER_DIR="/home/$(whoami)/actions-runner"
mkdir -p $RUNNER_DIR
cd $RUNNER_DIR

# 下载最新的GitHub Actions Runner
echo "📥 下载GitHub Actions Runner..."
RUNNER_VERSION=$(curl -s https://api.github.com/repos/actions/runner/releases/latest | grep tag_name | cut -d '"' -f 4 | sed 's/v//')
wget -O actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz

# 解压
tar xzf ./actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz

# 安装依赖
echo "📦 安装依赖..."
sudo ./bin/installdependencies.sh

# 配置runner
echo ""
echo "🔧 配置Runner..."
echo "请在GitHub仓库设置页面获取Runner token："
echo "👉 https://github.com/$GITHUB_USERNAME/$REPO_NAME/settings/actions/runners/new"
echo ""
read -p "请输入Runner token: " RUNNER_TOKEN

# 配置runner
./config.sh --url https://github.com/$GITHUB_USERNAME/$REPO_NAME --token $RUNNER_TOKEN --name "debian-server" --work _work --replace

# 创建systemd服务
echo "⚙️ 创建systemd服务..."
sudo ./svc.sh install $(whoami)
sudo ./svc.sh start

echo "✅ GitHub Actions Runner 设置完成！"
echo ""
echo "📋 接下来的步骤："
echo "1. 在GitHub仓库中验证Runner状态"
echo "2. 推送代码触发自动部署"
echo "3. 监控部署日志"
echo ""
echo "🔍 检查Runner状态: sudo ./svc.sh status"
echo "📊 查看Runner日志: journalctl -u actions.runner.$GITHUB_USERNAME-$REPO_NAME.debian-server -f"