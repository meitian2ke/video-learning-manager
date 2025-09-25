import asyncio
import os
import re
import platform
from typing import Dict, Tuple, Optional, List
from pathlib import Path
import subprocess
import json
from faster_whisper import WhisperModel
from app.core.config import settings
from app.utils.system_monitor import system_monitor
import logging

# 本地转录专用，移除第三方API依赖

logger = logging.getLogger(__name__)

# 创建信号量控制并发转录数量
transcription_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_TRANSCRIPTIONS)

class AITranscriptionService:
    def __init__(self):
        self.model = None  # 单一模型实例
        self.current_mode = None
        self.model_name = settings.WHISPER_MODEL  # 使用配置的模型
        self.environment = self._detect_environment()
        # 不在初始化时加载模型，采用懒加载模式
        logger.info(f"🔧 AI转录服务初始化 - 环境: {self.environment}, 模型: {self.model_name}")
    
    def _detect_environment(self) -> str:
        """检测运行环境"""
        if settings.ENVIRONMENT != "auto":
            return settings.ENVIRONMENT
        
        # 基于操作系统和硬件自动检测
        system = platform.system().lower()
        if system == "darwin":  # macOS
            return "development"
        elif system == "linux":
            # 检查是否有GPU
            if system_monitor.gpu_available:
                return "production"
            else:
                return "development"
        else:
            return "development"
    
    def _choose_transcription_mode(self) -> str:
        """智能选择转录模式（仅本地）"""
        # 检查系统负载
        can_transcribe, status_msg = system_monitor.is_suitable_for_transcription()
        
        if not can_transcribe:
            logger.warning(f"⚠️ 系统负载过高，但仍使用本地转录: {status_msg}")
        
        return "local"  # 只支持本地转录
    
    def _ensure_model_loaded(self):
        """确保模型已加载（懒加载）"""
        if self.model is None:
            try:
                # 智能选择设备和计算类型
                device = self._choose_device()
                compute_type = self._choose_compute_type()
                
                logger.info(f"🤖 正在加载Whisper模型: {settings.WHISPER_MODEL}")
                logger.info(f"🎯 设备: {device}, 计算类型: {compute_type}")
                
                # 支持两种加载方式：模型名称 或 本地路径
                model_path_or_name = self._get_model_path_or_name()
                
                self.model = WhisperModel(
                    model_path_or_name,
                    device=device,
                    compute_type=compute_type,
                    num_workers=getattr(settings, 'WHISPER_NUM_WORKERS', 1),
                    cpu_threads=getattr(settings, 'WHISPER_THREADS', 2)
                )
                logger.info(f"✅ Whisper模型 {settings.WHISPER_MODEL} 加载成功")
            except Exception as e:
                logger.error(f"❌ Whisper模型加载失败: {e}")
                raise Exception(f"模型未安装或损坏，请先手动下载模型: {e}")
        return self.model
    
    def _get_model_path_or_name(self) -> str:
        """获取模型路径或名称"""
        # 如果是large模型，尝试使用本地路径加载large-v3
        if settings.WHISPER_MODEL == "large":
            local_model_path = "/root/.cache/huggingface/hub/models--Systran--faster-whisper-large-v3"
            if os.path.exists(local_model_path):
                logger.info(f"🎯 使用本地large-v3模型: {local_model_path}")
                return local_model_path
            else:
                logger.info(f"🎯 本地模型不存在，使用标准large模型")
                return "large"
        
        # 其他情况直接使用模型名称
        return settings.WHISPER_MODEL
    
    def _choose_device(self) -> str:
        """智能选择计算设备"""
        if settings.WHISPER_DEVICE != "auto":
            return settings.WHISPER_DEVICE
        
        if settings.FORCE_CPU_MODE:
            return "cpu"
        
        if self.environment == "production" and system_monitor.gpu_available:
            return "cuda"
        else:
            return "cpu"
    
    def _choose_compute_type(self) -> str:
        """智能选择计算类型"""
        if settings.WHISPER_COMPUTE_TYPE != "auto":
            return settings.WHISPER_COMPUTE_TYPE
        
        device = self._choose_device()
        
        if device == "cuda":
            # GPU环境，使用float16以获得更好性能
            return "float16"
        else:
            # CPU环境，使用int8以节省内存和提高速度
            return "int8"
    
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
        """清理文本 - 增强版本，按句号分行，提升可读性"""
        # 去除多余空白
        text = re.sub(r'\s+', ' ', text)
        
        # 去除常见的无意义词汇和填充词
        noise_words = ['嗯', '啊', '呃', '这个', '那个', '然后', '就是', '我们', '你们']
        for word in noise_words:
            text = text.replace(word, '')
        
        # 智能断句 - 按标点符号分行
        text = re.sub(r'([。！？；])\s*', r'\1\n', text)
        
        # 处理逗号 - 适当添加换行提升可读性
        text = re.sub(r'([，,])\s*([A-Z]|\d+|[一-龯]{3,})', r'\1\n\2', text)
        
        # 清理多余的空行和空格
        text = re.sub(r'\n\s*\n', '\n', text)
        text = re.sub(r'^\s+|\s+$', '', text, flags=re.MULTILINE)
        
        return text.strip()
    
    def _generate_summary(self, text: str) -> str:
        """生成智能摘要"""
        sentences = text.replace('\n', '').split('。')
        
        # 过滤有效句子
        valid_sentences = [s.strip() for s in sentences if len(s.strip()) > 15]
        
        if not valid_sentences:
            return "无法生成摘要"
        
        # 智能选择关键句子（包含数字、公司名、产品名的句子优先）
        important_keywords = ['万', '亿', '元', '美元', '开发者', '平台', '框架', '开源', 'AI', 'API']
        scored_sentences = []
        
        for sentence in valid_sentences[:8]:  # 最多分析前8句
            score = 0
            # 包含重要关键词的句子得分更高
            for keyword in important_keywords:
                if keyword in sentence:
                    score += 1
            # 句子长度适中的得分更高
            if 20 <= len(sentence) <= 80:
                score += 1
            scored_sentences.append((score, sentence))
        
        # 按得分排序，取前3句
        scored_sentences.sort(key=lambda x: x[0], reverse=True)
        summary_sentences = [s[1] for s in scored_sentences[:3]]
        
        return '。'.join(summary_sentences) + '。'
    
    def _extract_tags(self, text: str) -> List[str]:
        """智能提取关键词标签和主题分类"""
        # 扩展的技术和商业关键词库
        keyword_categories = {
            'AI技术': ['AI', '人工智能', '机器学习', '深度学习', '神经网络', 'GPT', 'LLM', '大模型'],
            '编程开发': ['Python', 'JavaScript', 'React', 'Vue', 'Node.js', 'Django', 'FastAPI', 
                      '编程', '开发', '前端', '后端', '框架', 'API', '算法', '数据结构'],
            '工具平台': ['GitHub', 'Docker', 'Git', 'Linux', '部署', '测试', 'CI/CD', '云服务'],
            '数据爬虫': ['爬虫', '数据抓取', '网页', '数据清洗', '结构化数据', 'web数据'],
            '商业投资': ['融资', '投资', '万美元', '亿', '创业', 'YC', 'Nexus', '估值'],
            '产品服务': ['平台', '服务', '用户', '开发者', '企业', 'SaaS', '开源']
        }
        
        tags = []
        text_clean = text.replace('\n', ' ').lower()
        
        # 按分类提取关键词
        for category, keywords in keyword_categories.items():
            found_in_category = []
            for keyword in keywords:
                if keyword.lower() in text_clean or keyword in text:
                    found_in_category.append(keyword)
            
            # 如果该分类下有关键词，添加分类标签
            if found_in_category:
                tags.append(category)
                # 添加具体的关键词（最多2个）
                tags.extend(found_in_category[:2])
        
        # 数字信息提取
        import re
        numbers = re.findall(r'\d+[万亿]?[美元元]?', text)
        if numbers:
            tags.append('数据指标')
        
        # 去重并限制数量
        unique_tags = list(dict.fromkeys(tags))  # 保持顺序去重
        return unique_tags[:8]  # 最多返回8个标签
    
    def _generate_smart_title(self, text: str) -> str:
        """智能生成视频标题"""
        # 提取关键信息来生成标题
        sentences = text.replace('\n', '').split('。')
        
        if not sentences:
            return "视频内容摘要"
        
        first_sentence = sentences[0].strip()
        
        # 查找公司名、产品名、技术名等关键信息
        key_entities = []
        
        # 公司和产品名称
        companies = ['YC', 'Firecrawl', 'Nexus', 'GitHub', 'OpenAI', 'Google', 'Meta', 'Apple']
        for company in companies:
            if company in text:
                key_entities.append(company)
        
        # 技术关键词
        tech_terms = ['AI', '爬虫', '大模型', 'API', '开源', '平台', '框架']
        for term in tech_terms:
            if term in text:
                key_entities.append(term)
        
        # 数字信息
        import re
        numbers = re.findall(r'\d+[万亿美元]+', text)
        if numbers:
            key_entities.extend(numbers[:2])  # 最多添加2个数字
        
        # 生成标题
        if key_entities:
            # 优先使用前30个字符 + 关键实体
            base_title = first_sentence[:30]
            entities_str = " | ".join(key_entities[:3])  # 最多3个关键实体
            return f"{base_title} - {entities_str}"
        else:
            # 如果没有关键实体，使用前50个字符
            return first_sentence[:50] + ("..." if len(first_sentence) > 50 else "")
    
    def _calculate_importance_score(self, text: str, tags: List[str]) -> float:
        """计算重要性评分 (1.0-5.0)"""
        score = 3.0  # 基础分数
        
        # 基于内容长度评分 (详细的内容通常更重要)
        if len(text) > 1000:
            score += 0.5
        elif len(text) < 200:
            score -= 0.5
        
        # 基于标签数量和质量评分
        high_value_tags = ['AI技术', '商业投资', '数据指标']
        medium_value_tags = ['编程开发', '工具平台', '产品服务']
        
        for tag in tags:
            if tag in high_value_tags:
                score += 0.8
            elif tag in medium_value_tags:
                score += 0.4
        
        # 基于关键词密度评分
        important_keywords = ['万美元', '亿', '融资', '开源', 'AI', '平台', 'API']
        keyword_count = sum(1 for keyword in important_keywords if keyword in text)
        score += min(keyword_count * 0.2, 1.0)
        
        # 基于数字信息评分 (包含具体数据的内容更有价值)
        import re
        numbers = re.findall(r'\d+[万亿美元元]+', text)
        if numbers:
            score += 0.6
        
        # 确保分数在1.0-5.0范围内
        return max(1.0, min(5.0, score))
    
    def _format_text_for_display(self, text: str) -> str:
        """格式化文本用于显示，增强可读性"""
        # 按句号分段，每句一行
        sentences = text.split('。')
        formatted_lines = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # 检测重要信息并加粗标记
            if self._is_important_sentence(sentence):
                formatted_lines.append(f"**{sentence}。**")
            else:
                formatted_lines.append(f"{sentence}。")
        
        return '\n'.join(formatted_lines)
    
    def _is_important_sentence(self, sentence: str) -> bool:
        """判断句子是否重要（用于加粗显示）"""
        important_indicators = [
            r'\d+[万亿][美元元]',  # 金额数字
            r'\d+万[开发者用户]',  # 用户数量
            r'开源|GitHub',  # 开源相关
            r'平台|框架|API',  # 技术平台
            r'YC|Nexus|领[头投]',  # 投资机构
        ]
        
        for pattern in important_indicators:
            if re.search(pattern, sentence):
                return True
        
        return False
    
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
        """智能转录视频文件（带并发控制和负载监控）"""
        async with transcription_semaphore:  # 控制并发数量
            try:
                logger.info(f"🎬 开始转录视频: {os.path.basename(video_path)}")
                logger.info(f"📊 当前可用槽位: {transcription_semaphore._value}")
                
                # 记录系统状态
                system_monitor.log_system_status()
                
                # 智能选择转录模式
                mode = self._choose_transcription_mode()
                self.current_mode = mode
                
                logger.info(f"🤖 选择转录模式: {mode}")
                logger.info(f"🏗️ 运行环境: {self.environment}")
                
                logger.info("💻 === 使用本地Whisper模型转录 ===")
                result = await self._transcribe_with_local_model(video_path)
                logger.info("✅ === 本地转录完成 ===")
                
                # 转录后再次记录系统状态
                system_monitor.log_system_status()
                
                return result
                    
            except Exception as e:
                logger.error(f"❌ 转录视频失败: {e} (释放槽位)")
                return {
                    "original_text": f"转录失败: {str(e)}",
                    "cleaned_text": f"转录失败: {str(e)}",
                    "formatted_text": f"转录失败: {str(e)}",
                    "summary": "视频转录过程中发生错误",
                    "smart_title": "转录失败",
                    "tags": "转录失败",
                    "importance_score": 1.0,
                    "language": "zh",
                    "confidence_score": 0.0,
                    "segments": []
                }
    
    
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
            
            # 智能文本处理和分析
            cleaned_text = self._clean_text(full_text)
            formatted_text = self._format_text_for_display(cleaned_text)
            summary = self._generate_summary(cleaned_text)
            tags = self._extract_tags(cleaned_text)
            smart_title = self._generate_smart_title(cleaned_text)
            importance_score = self._calculate_importance_score(cleaned_text, tags)
            
            logger.info(f"✅ 本地转录完成，共转录 {len(transcript_segments)} 个片段，重要性评分: {importance_score:.1f}")
            
            return {
                "original_text": full_text.strip(),
                "cleaned_text": cleaned_text,
                "formatted_text": formatted_text,
                "summary": summary,
                "smart_title": smart_title,
                "tags": ", ".join(tags),
                "importance_score": importance_score,
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