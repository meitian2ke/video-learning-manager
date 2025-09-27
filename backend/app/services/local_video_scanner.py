"""
本地视频扫描服务
自动扫描指定目录的新增视频并添加到处理队列
"""

import os
import asyncio
import hashlib
from typing import List, Set
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging
from sqlalchemy.orm import Session

from app.core.database import get_db, Video, LearningRecord, Transcript
from app.models.schemas import VideoCreate
from app.services.ai_service import ai_service

logger = logging.getLogger(__name__)

class VideoFileHandler(FileSystemEventHandler):
    """视频文件事件处理器"""
    
    SUPPORTED_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', '.m4v'}
    
    def __init__(self, scanner_service):
        self.scanner_service = scanner_service
        
    def on_created(self, event):
        """文件创建事件"""
        if not event.is_directory and self._is_video_file(event.src_path):
            logger.info(f"检测到新视频文件: {event.src_path}")
            self._schedule_processing(event.src_path)
    
    def on_moved(self, event):
        """文件移动事件"""
        if not event.is_directory and self._is_video_file(event.dest_path):
            logger.info(f"检测到移动的视频文件: {event.dest_path}")
            self._schedule_processing(event.dest_path)
    
    def _schedule_processing(self, file_path: str):
        """安排处理任务（线程安全）"""
        try:
            # 使用线程池执行器来处理异步任务
            import threading
            import concurrent.futures
            
            def run_processing():
                # 创建新的事件循环
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self.scanner_service.process_new_video(file_path))
                finally:
                    loop.close()
            
            # 在线程池中执行
            thread = threading.Thread(target=run_processing)
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            logger.error(f"安排处理任务失败: {e}")
    
    def _is_video_file(self, file_path: str) -> bool:
        """检查是否为支持的视频文件（过滤缓存文件）"""
        file_path_obj = Path(file_path)
        
        # 过滤系统缓存文件和临时文件
        if file_path_obj.name.startswith('._'):
            logger.debug(f"跳过缓存文件: {file_path_obj.name}")
            return False
        if file_path_obj.name.startswith('.DS_Store'):
            logger.debug(f"跳过系统文件: {file_path_obj.name}")
            return False
        if any(file_path_obj.name.endswith(ext) for ext in ['.tmp', '.partial', '.crdownload']):
            logger.debug(f"跳过临时文件: {file_path_obj.name}")
            return False
            
        return file_path_obj.suffix.lower() in self.SUPPORTED_EXTENSIONS

class LocalVideoScanner:
    """本地视频扫描器"""
    
    def __init__(self, watch_directory: str):
        self.watch_directory = Path(watch_directory)
        self.processed_files: Set[str] = set()
        self.observer = None
        self.handler = VideoFileHandler(self)
        
        # 确保监控目录存在
        self.watch_directory.mkdir(parents=True, exist_ok=True)
        
        # 加载已处理文件记录
        self._load_processed_files()
    
    def _load_processed_files(self):
        """加载已处理的文件记录"""
        cache_file = self.watch_directory / '.processed_videos.txt'
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                self.processed_files = set(line.strip() for line in f.readlines())
    
    def _save_processed_files(self):
        """保存已处理的文件记录"""
        cache_file = self.watch_directory / '.processed_videos.txt'
        with open(cache_file, 'w', encoding='utf-8') as f:
            for file_hash in self.processed_files:
                f.write(f"{file_hash}\\n")
    
    def _get_file_hash(self, file_path: str) -> str:
        """获取文件哈希值（用于缓存）"""
        hasher = hashlib.md5()
        file_path_obj = Path(file_path)
        
        # 使用文件路径、大小和修改时间生成哈希
        stat = file_path_obj.stat()
        hash_input = f"{file_path_obj.name}_{stat.st_size}_{stat.st_mtime}"
        hasher.update(hash_input.encode())
        return hasher.hexdigest()
    
    def _get_file_fingerprint(self, file_path: str) -> str:
        """获取文件内容指纹（SHA256）"""
        sha256_hash = hashlib.sha256()
        file_path_obj = Path(file_path)
        
        try:
            with open(file_path_obj, "rb") as f:
                # 分块读取文件以处理大文件
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"计算文件指纹失败: {file_path}, 错误: {e}")
            # 如果读取失败，使用文件大小和修改时间作为后备
            stat = file_path_obj.stat()
            fallback_input = f"{file_path_obj.name}_{stat.st_size}_{stat.st_mtime}"
            return hashlib.sha256(fallback_input.encode()).hexdigest()
    
    async def scan_existing_videos(self) -> List[str]:
        """扫描现有的视频文件"""
        video_files = []
        
        for file_path in self.watch_directory.rglob('*'):
            if file_path.is_file() and self._is_video_file(str(file_path)):
                file_hash = self._get_file_hash(str(file_path))
                if file_hash not in self.processed_files:
                    video_files.append(str(file_path))
        
        logger.info(f"发现 {len(video_files)} 个未处理的视频文件")
        return video_files
    
    async def process_new_video(self, file_path: str):
        """处理新增的视频文件"""
        try:
            file_hash = self._get_file_hash(file_path)
            
            # 检查是否已处理（缓存检查）
            if file_hash in self.processed_files:
                logger.debug(f"文件已处理（缓存），跳过: {file_path}")
                return
            
            # 等待文件写入完成
            await self._wait_for_file_complete(file_path)
            
            # 计算文件内容指纹
            file_fingerprint = self._get_file_fingerprint(file_path)
            logger.info(f"计算文件指纹: {file_path} -> {file_fingerprint}")
            
            # 检查数据库中是否已存在相同指纹的视频
            if await self._check_duplicate_fingerprint(file_fingerprint):
                logger.info(f"检测到重复视频（指纹相同），跳过: {file_path}")
                # 将此文件添加到已处理缓存，避免重复检查
                self.processed_files.add(file_hash)
                self._save_processed_files()
                return
            
            # 创建视频记录
            video_data = {
                "url": f"file://{file_path}",
                "title": Path(file_path).stem,
                "platform": "local",
                "priority": 3,
                "file_fingerprint": file_fingerprint
            }
            
            # 添加到处理队列
            result = await self._add_to_processing_queue(video_data, file_path)
            
            if result:
                self.processed_files.add(file_hash)
                self._save_processed_files()
                logger.info(f"本地视频添加成功: {file_path}")
            
        except Exception as e:
            logger.error(f"处理本地视频失败: {file_path}, 错误: {e}")
    
    async def _wait_for_file_complete(self, file_path: str, max_wait: int = 30):
        """等待文件写入完成"""
        file_path_obj = Path(file_path)
        previous_size = 0
        stable_count = 0
        
        for _ in range(max_wait):
            if not file_path_obj.exists():
                await asyncio.sleep(1)
                continue
                
            current_size = file_path_obj.stat().st_size
            if current_size == previous_size:
                stable_count += 1
                if stable_count >= 3:  # 文件大小稳定3秒
                    break
            else:
                stable_count = 0
                previous_size = current_size
            
            await asyncio.sleep(1)
    
    async def _check_duplicate_fingerprint(self, fingerprint: str) -> bool:
        """检查数据库中是否已存在相同指纹的视频"""
        try:
            from app.core.database import SessionLocal, Video
            
            db = SessionLocal()
            try:
                existing_video = db.query(Video).filter(Video.file_fingerprint == fingerprint).first()
                return existing_video is not None
            finally:
                db.close()
        except Exception as e:
            logger.error(f"检查重复指纹失败: {e}")
            return False
    
    async def _add_to_processing_queue(self, video_data: dict, file_path: str) -> bool:
        """添加到视频处理队列并自动开始处理"""
        try:
            logger.info(f"自动处理本地视频: {video_data}")
            
            # 创建视频记录
            from app.core.database import SessionLocal, Video, LearningRecord
            from datetime import datetime
            
            db = SessionLocal()
            try:
                # 检查是否已存在
                existing_video = db.query(Video).filter(Video.url == video_data["url"]).first()
                if existing_video:
                    logger.info(f"视频已存在，跳过: {file_path}")
                    return True
                
                # 创建新视频记录
                video = Video(
                    url=video_data["url"],
                    title=video_data["title"],
                    platform=video_data["platform"],
                    local_path=file_path,
                    file_fingerprint=video_data["file_fingerprint"],
                    status="processing"  # 直接设置为处理中
                )
                db.add(video)
                db.flush()  # 获取ID
                
                # 创建学习记录
                learning_record = LearningRecord(
                    video_id=video.id,
                    priority=video_data["priority"],
                    learning_status="todo"
                )
                db.add(learning_record)
                db.commit()
                
                logger.info(f"视频记录创建成功，ID: {video.id}")
                
                # 异步启动处理任务
                try:
                    # 尝试在当前事件循环中创建任务
                    asyncio.create_task(self._process_video_async(video.id, file_path))
                except RuntimeError:
                    # 如果没有运行的事件循环，创建新线程处理
                    import threading
                    def run_processing():
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            loop.run_until_complete(self._process_video_async(video.id, file_path))
                        finally:
                            loop.close()
                    
                    thread = threading.Thread(target=run_processing)
                    thread.daemon = True
                    thread.start()
                
                return True
                
            except Exception as e:
                db.rollback()
                logger.error(f"创建视频记录失败: {e}")
                return False
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"添加视频到处理队列失败: {e}")
            return False
    
    async def _process_video_async(self, video_id: int, file_path: str):
        """异步处理视频"""
        try:
            from app.services.ai_service import ai_service
            from app.core.database import SessionLocal, Video
            
            logger.info(f"开始自动处理视频 ID: {video_id}, 路径: {file_path}")
            
            # 模拟处理进度
            db = SessionLocal()
            try:
                # 更新状态为处理中
                video = db.query(Video).filter(Video.id == video_id).first()
                if video:
                    video.status = "processing"
                    db.commit()
                
                # 真实的视频处理步骤
                logger.info(f"开始使用Whisper处理视频 {video_id}: {file_path}")
                
                from datetime import datetime
                import time
                start_time = time.time()
                
                try:
                    # 使用AI服务进行真实的字幕提取
                    logger.info(f"正在提取音频并转录字幕: {file_path}")
                    
                    # 直接对视频文件进行转录（faster-whisper支持直接处理视频）
                    transcript_data = await ai_service.transcribe_video(file_path)
                    
                    processing_time = int(time.time() - start_time)
                    logger.info(f"字幕提取完成，耗时 {processing_time} 秒")
                    
                    # 创建字幕记录
                    transcript = Transcript(
                        video_id=video_id,
                        original_text=transcript_data.get("original_text", ""),
                        cleaned_text=transcript_data.get("cleaned_text", transcript_data.get("original_text", "")),
                        summary=transcript_data.get("summary", ""),
                        tags=transcript_data.get("tags", ""),
                        language=transcript_data.get("language", "zh"),
                        confidence_score=transcript_data.get("confidence_score", 0.0),
                        processing_time=processing_time
                    )
                    db.add(transcript)
                    logger.info(f"字幕记录已保存到数据库")
                    
                except Exception as transcribe_error:
                    logger.error(f"字幕提取失败: {transcribe_error}")
                    # 即使字幕提取失败，也标记视频为已完成，但没有字幕
                    processing_time = int(time.time() - start_time)
                
                # 更新为完成状态
                if video:
                    video.status = "completed"
                    db.commit()
                    
            except Exception as e:
                logger.error(f"处理视频 {video_id} 失败: {e}")
                # 更新为失败状态
                video = db.query(Video).filter(Video.id == video_id).first()
                if video:
                    video.status = "failed"
                    db.commit()
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"异步处理视频失败: {e}")
    
    def _is_video_file(self, file_path: str) -> bool:
        """检查是否为支持的视频文件"""
        return Path(file_path).suffix.lower() in self.handler.SUPPORTED_EXTENSIONS
    
    def start_watching(self):
        """开始监控文件夹"""
        try:
            self.observer = Observer()
            self.observer.schedule(self.handler, str(self.watch_directory), recursive=True)
            self.observer.start()
            logger.info(f"开始监控视频目录: {self.watch_directory}")
        except Exception as e:
            logger.error(f"启动文件监控失败: {e}")
    
    def stop_watching(self):
        """停止监控"""
        if self.observer and self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
            logger.info("视频目录监控已停止")

# 全局扫描器实例
scanner = None

def get_scanner(watch_directory: str = None) -> LocalVideoScanner:
    """获取扫描器实例"""
    global scanner
    if scanner is None and watch_directory:
        scanner = LocalVideoScanner(watch_directory)
    return scanner