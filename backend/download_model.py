#!/usr/bin/env python3
"""
手动下载Whisper模型脚本
运行方式：python download_model.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.ai_service import ai_service
from app.core.config import settings
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """主函数"""
    print("=" * 60)
    print("🤖 Whisper模型下载工具")
    print("=" * 60)
    print(f"模型: {settings.WHISPER_MODEL}")
    print(f"设备: {settings.WHISPER_DEVICE}")
    print(f"计算类型: {settings.WHISPER_COMPUTE_TYPE}")
    print("=" * 60)
    
    print("开始下载模型，这可能需要几分钟...")
    print("模型大小约1.5GB，请确保网络连接稳定")
    print("-" * 60)
    
    try:
        success = ai_service.download_model()
        if success:
            print("✅ 模型下载成功！")
            print("现在可以重启后端服务使用AI功能了")
        else:
            print("❌ 模型下载失败！")
            print("请检查网络连接或稍后重试")
            return 1
    except Exception as e:
        print(f"❌ 下载过程中出现错误: {e}")
        return 1
    
    print("=" * 60)
    return 0

if __name__ == "__main__":
    exit(main())