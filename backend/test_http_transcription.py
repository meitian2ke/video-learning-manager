#!/usr/bin/env python3
"""
测试本地Whisper模型转录功能
"""
import asyncio
import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.append('/Users/user/Documents/AI-MCP-Store/video-learning-manager/backend')

from app.services.ai_service import ai_service

async def test_local_transcription():
    """测试本地Whisper模型的转录"""
    
    # 选择一个小视频文件进行测试
    test_video = "/Users/user/Documents/AI-MCP-Store/video-learning-manager/local-videos/Cline一键部署G_20250911183841.mp4"
    
    if not os.path.exists(test_video):
        print(f"❌ 测试视频文件不存在: {test_video}")
        return
    
    print(f"🎬 开始测试视频转录: {os.path.basename(test_video)}")
    print(f"📁 文件大小: {os.path.getsize(test_video) / (1024*1024):.1f} MB")
    print("💻 使用本地Whisper模型进行转录...")
    
    try:
        # 测试转录
        result = await ai_service.transcribe_video(test_video)
        
        print("\n✅ === 本地转录测试成功 ===")
        print(f"🔤 原始文本长度: {len(result.get('original_text', ''))}")
        print(f"✨ 清理文本长度: {len(result.get('cleaned_text', ''))}")
        print(f"📋 格式化文本长度: {len(result.get('formatted_text', ''))}")
        print(f"📝 智能标题: {result.get('smart_title', 'N/A')}")
        print(f"🏷️  标签: {result.get('tags', 'N/A')}")
        print(f"⭐ 重要性评分: {result.get('importance_score', 'N/A')}")
        print(f"🎯 置信度: {result.get('confidence_score', 'N/A')}")
        print(f"🗣️  语言: {result.get('language', 'N/A')}")
        print(f"📊 分段数量: {len(result.get('segments', []))}")
        
        # 显示格式化文本的前几行
        formatted_text = result.get('formatted_text', '')
        if formatted_text:
            lines = formatted_text.split('\n')[:5]
            print(f"\n📖 格式化文本预览（前5行）:")
            for i, line in enumerate(lines, 1):
                print(f"  {i}. {line}")
        
        print(f"\n📄 摘要: {result.get('summary', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ === 本地转录测试失败 ===")
        print(f"❗ 错误信息: {e}")
        import traceback
        print(f"🔍 详细错误: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    print("🚀 启动本地转录测试...")
    success = asyncio.run(test_local_transcription())
    
    if success:
        print("\n🎉 本地转录测试完成！")
    else:
        print("\n💥 本地转录测试失败！")
        sys.exit(1)