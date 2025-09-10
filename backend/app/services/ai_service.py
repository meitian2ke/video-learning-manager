import asyncio
import os
import re
from typing import Dict, Tuple, Optional
from pathlib import Path
import subprocess
import json
from faster_whisper import WhisperModel
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class AITranscriptionService:
    def __init__(self):
        self.model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """初始化Whisper模型"""
        try:
            self.model = WhisperModel(
                settings.WHISPER_MODEL,
                device=settings.WHISPER_DEVICE,
                compute_type=settings.WHISPER_COMPUTE_TYPE
            )
            logger.info(f"Whisper模型 {settings.WHISPER_MODEL} 初始化成功")
        except Exception as e:
            logger.error(f"Whisper模型初始化失败: {e}")
            raise
    
    async def download_video(self, url: str, video_id: int) -> Tuple[str, Dict]:
        """下载视频并获取信息"""
        try:
            output_dir = Path(settings.VIDEO_DIR) / str(video_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # yt-dlp 命令
            cmd = [
                "yt-dlp",
                "--extract-flat",  # 只获取信息，不下载
                "--dump-json",
                url
            ]
            
            # 获取视频信息
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                raise Exception(f"获取视频信息失败: {stderr.decode()}")
            
            video_info = json.loads(stdout.decode())
            
            # 下载视频
            download_cmd = [
                "yt-dlp",
                "--format", "best[height<=720]",  # 限制画质以节省空间
                "--output", str(output_dir / "%(title)s.%(ext)s"),
                "--write-thumbnail",
                url
            ]
            
            download_result = await asyncio.create_subprocess_exec(
                *download_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            await download_result.communicate()
            
            if download_result.returncode != 0:
                raise Exception("视频下载失败")
            
            # 查找下载的文件
            video_files = list(output_dir.glob("*"))
            video_file = next((f for f in video_files if f.suffix in ['.mp4', '.webm', '.mkv']), None)
            
            if not video_file:
                raise Exception("未找到下载的视频文件")
            
            return str(video_file), {
                "title": video_info.get("title", ""),
                "duration": video_info.get("duration", 0),
                "thumbnail": video_info.get("thumbnail", ""),
                "platform": self._detect_platform(url)
            }
            
        except Exception as e:
            logger.error(f"下载视频失败: {e}")
            raise
    
    async def extract_audio(self, video_path: str) -> str:
        """从视频中提取音频"""
        try:
            video_file = Path(video_path)
            audio_path = Path(settings.AUDIO_DIR) / f"{video_file.stem}.wav"
            
            # 确保音频目录存在
            audio_path.parent.mkdir(parents=True, exist_ok=True)
            
            # FFmpeg 提取音频
            cmd = [
                "ffmpeg",
                "-i", str(video_file),
                "-ac", "1",  # 单声道
                "-ar", "16000",  # 16kHz采样率
                "-y",  # 覆盖已存在文件
                str(audio_path)
            ]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            await result.communicate()
            
            if result.returncode != 0 or not audio_path.exists():
                raise Exception("音频提取失败")
            
            return str(audio_path)
            
        except Exception as e:
            logger.error(f"提取音频失败: {e}")
            raise
    
    async def transcribe_audio(self, audio_path: str) -> Dict:
        """转录音频为文字"""
        try:
            if not self.model:
                self._initialize_model()
            
            # 执行转录
            segments, info = self.model.transcribe(audio_path)
            
            # 收集转录结果
            transcript_segments = []
            full_text = ""
            
            for segment in segments:
                segment_data = {
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip()
                }
                transcript_segments.append(segment_data)
                full_text += segment.text.strip() + " "
            
            # 清理文本
            cleaned_text = self._clean_text(full_text)
            
            # 生成摘要和标签
            summary = self._generate_summary(cleaned_text)
            tags = self._extract_tags(cleaned_text)
            
            return {
                "original_text": full_text.strip(),
                "cleaned_text": cleaned_text,
                "summary": summary,
                "tags": ", ".join(tags),
                "language": info.language,
                "confidence_score": info.language_probability,
                "segments": transcript_segments
            }
            
        except Exception as e:
            logger.error(f"转录音频失败: {e}")
            raise
    
    def _clean_text(self, text: str) -> str:
        """清理文本"""
        # 去除多余空白
        text = re.sub(r'\s+', ' ', text)
        
        # 去除常见的无意义词汇
        noise_words = ['嗯', '啊', '呃', '这个', '那个', '然后']
        for word in noise_words:
            text = text.replace(word, '')
        
        # 添加标点符号
        text = re.sub(r'([。！？])\s*', r'\1\n', text)
        
        return text.strip()
    
    def _generate_summary(self, text: str) -> str:
        """生成摘要（简单版本，可后续用LLM优化）"""
        sentences = text.split('。')
        # 取前3个有效句子作为摘要
        summary_sentences = [s.strip() for s in sentences[:3] if len(s.strip()) > 10]
        return '。'.join(summary_sentences) + '。'
    
    def _extract_tags(self, text: str) -> List[str]:
        """提取关键词标签"""
        # 简单的关键词提取
        tech_keywords = [
            'Python', 'JavaScript', 'React', 'Vue', 'Node.js', 'Django', 'FastAPI',
            'Docker', 'Git', 'Linux', '编程', '开发', '前端', '后端', '数据库',
            '部署', '测试', '框架', 'API', '算法', '数据结构'
        ]
        
        tags = []
        text_lower = text.lower()
        
        for keyword in tech_keywords:
            if keyword.lower() in text_lower or keyword in text:
                tags.append(keyword)
        
        return tags[:5]  # 最多返回5个标签
    
    def _detect_platform(self, url: str) -> str:
        """检测视频平台"""
        url_lower = url.lower()
        
        if 'douyin.com' in url_lower or 'tiktok.com' in url_lower:
            return 'douyin'
        elif 'weixin' in url_lower or 'mp.weixin.qq.com' in url_lower:
            return 'weixin'
        elif 'bilibili.com' in url_lower:
            return 'bilibili'
        elif 'youtube.com' in url_lower or 'youtu.be' in url_lower:
            return 'youtube'
        elif 'xiaohongshu.com' in url_lower:
            return 'xiaohongshu'
        else:
            return 'unknown'
    
    async def cleanup_files(self, video_id: int):
        """清理临时文件"""
        try:
            video_dir = Path(settings.VIDEO_DIR) / str(video_id)
            audio_files = Path(settings.AUDIO_DIR).glob(f"{video_id}_*.wav")
            
            # 删除音频文件（保留视频文件用于后续需要）
            for audio_file in audio_files:
                if audio_file.exists():
                    audio_file.unlink()
            
            logger.info(f"清理视频 {video_id} 的临时文件完成")
            
        except Exception as e:
            logger.warning(f"清理临时文件失败: {e}")

# 全局服务实例
ai_service = AITranscriptionService()