#!/bin/bash
# 🚀 一键提交推送脚本， 测试推送

# 默认提交信息
msg="$1"
if [ -z "$msg" ]; then
  msg="自动提交 $(date '+%Y-%m-%d %H:%M:%S')"
fi

echo "======================================="
echo "📦 提交说明: $msg"
echo "======================================="

git add .
git commit -m "$msg"
git push lan main

echo "✅ 推送完成！"