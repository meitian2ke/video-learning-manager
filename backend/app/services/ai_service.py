import asyncio
import os
import re
from typing import Dict, Tuple, Optional, List
from pathlib import Path
import subprocess
import json
from faster_whisper import WhisperModel
from app.core.config import settings
import logging

# OpenAI API client - 延迟初始化避免启动问题
openai_client = None
try:
    from openai import OpenAI
    # 延迟到实际使用时再初始化
except ImportError:
    pass

logger = logging.getLogger(__name__)

# 创建信号量控制并发转录数量
transcription_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_TRANSCRIPTIONS)

class AITranscriptionService:
    def __init__(self):
        self.model = None
        # 不在初始化时加载模型，采用懒加载模式
    
    def _ensure_model_loaded(self):
        """确保模型已加载（懒加载）"""
        if self.model is None:
            try:
                logger.info(f"正在加载Whisper模型: {settings.WHISPER_MODEL}")
                self.model = WhisperModel(
                    settings.WHISPER_MODEL,
                    device=settings.WHISPER_DEVICE,
                    compute_type=settings.WHISPER_COMPUTE_TYPE,
                    num_workers=getattr(settings, 'WHISPER_NUM_WORKERS', 1),
                    cpu_threads=getattr(settings, 'WHISPER_THREADS', 2)
                )
                logger.info(f"Whisper模型 {settings.WHISPER_MODEL} 加载成功")
            except Exception as e:
                logger.error(f"Whisper模型加载失败: {e}")
                raise Exception(f"模型未安装或损坏，请先手动下载模型: {e}")
        return self.model
    
    def download_model(self):
        """手动下载模型"""
        try:
            logger.info(f"开始下载Whisper模型: {settings.WHISPER_MODEL}")
            # 这会触发模型下载
            model = WhisperModel(
                settings.WHISPER_MODEL,
                device=settings.WHISPER_DEVICE,
                compute_type=settings.WHISPER_COMPUTE_TYPE,
                num_workers=getattr(settings, 'WHISPER_NUM_WORKERS', 1),
                cpu_threads=getattr(settings, 'WHISPER_THREADS', 2)
            )
            self.model = model
            logger.info("模型下载并加载成功")
            return True
        except Exception as e:
            logger.error(f"模型下载失败: {e}")
            return False
    
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
        """转录音频为文字（带并发控制）"""
        async with transcription_semaphore:  # 控制并发数量
            try:
                logger.info(f"开始转录音频: {audio_path} (当前可用槽位: {transcription_semaphore._value})")
                
                if not self.model:
                    self._ensure_model_loaded()
                
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
                
                logger.info(f"转录完成，共转录 {len(transcript_segments)} 个片段 (释放槽位)")
                
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
                logger.error(f"转录音频失败: {e} (释放槽位)")
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
    
    async def transcribe_video(self, video_path: str) -> Dict:
        """直接转录视频文件（带并发控制）"""
        async with transcription_semaphore:  # 控制并发数量
            try:
                logger.info(f"开始转录视频: {video_path} (当前可用槽位: {transcription_semaphore._value})")
                
                # 根据配置选择转录方式，支持自动降级
                if settings.TRANSCRIPTION_MODE == "openai":
                    logger.info("🌐 === 使用OpenAI云端转录模式 === 🌐")
                    logger.info(f"📂 视频文件: {video_path}")
                    logger.info(f"🔑 API端点: {settings.OPENAI_BASE_URL}")
                    try:
                        result = await self._transcribe_with_openai(video_path)
                        logger.info("✅ === OpenAI云端转录完成 === ✅")
                        return result
                    except Exception as openai_error:
                        logger.error(f"❌ OpenAI转录失败，自动切换到本地模式: {openai_error}")
                        logger.warning("🔄 === 自动降级到本地CPU转录模式 === 🔄")
                        # 自动降级到本地模式
                        result = await self._transcribe_with_local_model(video_path)
                        logger.info("✅ === 本地CPU转录完成（降级模式）=== ✅")
                        return result
                else:
                    logger.info("💻 === 使用本地CPU转录模式 === 💻")
                    logger.info(f"📂 视频文件: {video_path}")
                    logger.warning("⚠️  注意：本地模式将消耗大量CPU资源！")
                    result = await self._transcribe_with_local_model(video_path)
                    logger.info("✅ === 本地CPU转录完成 === ✅")
                    return result
                    
            except Exception as e:
                logger.error(f"转录视频失败: {e} (释放槽位)")
                return {
                    "original_text": f"转录失败: {str(e)}",
                    "cleaned_text": f"转录失败: {str(e)}",
                    "summary": "视频转录过程中发生错误",
                    "tags": "转录失败",
                    "language": "zh",
                    "confidence_score": 0.0,
                    "segments": []
                }
    
    async def _transcribe_with_openai(self, video_path: str) -> Dict:
        """使用OpenAI API转录"""
        try:
            logger.info("正在使用OpenAI Whisper API转录视频...")
            
            # 延迟初始化OpenAI客户端
            global openai_client
            if openai_client is None:
                from openai import OpenAI
                openai_client = OpenAI(
                    api_key=settings.OPENAI_API_KEY,
                    base_url=settings.OPENAI_BASE_URL
                )
            
            # 检查文件大小 (OpenAI限制25MB)
            file_size = os.path.getsize(video_path)
            if file_size > 25 * 1024 * 1024:  # 25MB
                # 需要先提取音频并压缩
                audio_path = await self.extract_audio(video_path)
                transcribe_file = audio_path
            else:
                transcribe_file = video_path
            
            # 调用OpenAI API
            with open(transcribe_file, "rb") as audio_file:
                transcript = openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json",
                    language="zh"
                )
            
            # 处理响应
            full_text = transcript.text
            segments_data = []
            
            # 如果有segments信息
            if hasattr(transcript, 'segments') and transcript.segments:
                for segment in transcript.segments:
                    segments_data.append({
                        "start": segment.get('start', 0),
                        "end": segment.get('end', 0),
                        "text": segment.get('text', '').strip()
                    })
            else:
                # 如果没有segments，创建一个简单的segment
                segments_data.append({
                    "start": 0,
                    "end": 0,
                    "text": full_text
                })
            
            # 清理临时音频文件
            if transcribe_file != video_path and os.path.exists(transcribe_file):
                os.remove(transcribe_file)
            
            # 处理文本
            cleaned_text = self._clean_text(full_text)
            summary = self._generate_summary(cleaned_text)
            tags = self._extract_tags(cleaned_text)
            
            logger.info(f"OpenAI转录完成，共{len(segments_data)}个片段")
            
            return {
                "original_text": full_text,
                "cleaned_text": cleaned_text,
                "summary": summary,
                "tags": ", ".join(tags),
                "language": "zh",
                "confidence_score": 0.95,  # OpenAI通常很准确
                "segments": segments_data
            }
            
        except Exception as e:
            logger.error(f"OpenAI转录失败: {e}")
            raise
    
    async def _transcribe_with_local_model(self, video_path: str) -> Dict:
        """使用本地模型转录"""
        try:
            # 确保模型已加载
            self._ensure_model_loaded()
            
            # faster-whisper 可以直接处理视频文件
            logger.info("正在使用本地Whisper模型转录视频...")
            segments, info = self.model.transcribe(
                video_path,
                language="zh",  # 指定为中文
                task="transcribe"
            )
            
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
            
            if not full_text.strip():
                logger.warning("转录结果为空，可能是视频没有音频或音频质量问题")
                return {
                    "original_text": "未检测到音频内容",
                    "cleaned_text": "未检测到音频内容",
                    "summary": "该视频可能没有音频内容或音频质量较差",
                    "tags": "无音频",
                    "language": "zh",
                    "confidence_score": 0.0,
                    "segments": []
                }
            
            # 清理文本
            cleaned_text = self._clean_text(full_text)
            
            # 生成摘要和标签
            summary = self._generate_summary(cleaned_text)
            tags = self._extract_tags(cleaned_text)
            
            logger.info(f"本地转录完成，共转录 {len(transcript_segments)} 个片段")
            
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
            logger.error(f"转录视频失败: {e} (释放槽位)")
            # 返回错误信息而不是抛出异常
            return {
                "original_text": f"转录失败: {str(e)}",
                "cleaned_text": f"转录失败: {str(e)}",
                "summary": "视频转录过程中发生错误",
                "tags": "转录失败",
                "language": "zh",
                "confidence_score": 0.0,
                "segments": []
            }

# 全局服务实例
ai_service = AITranscriptionService()