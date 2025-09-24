"""
本地视频管理API
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from typing import List
import logging
from pathlib import Path

from app.core.config import settings
from app.services.local_video_scanner import get_scanner
from app.core.database import get_db, Video, Transcript
from sqlalchemy.orm import Session
from fastapi import Depends
import os

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/scan")
async def scan_local_videos(background_tasks: BackgroundTasks):
    """扫描本地视频文件夹"""
    try:
        logger.info(f"开始扫描本地视频目录: {settings.LOCAL_VIDEO_DIR}")
        
        scanner = get_scanner(settings.LOCAL_VIDEO_DIR)
        if not scanner:
            logger.error("视频扫描器初始化失败")
            raise HTTPException(status_code=500, detail="视频扫描器初始化失败")
        
        # 扫描现有视频
        video_files = await scanner.scan_existing_videos()
        logger.info(f"扫描完成，发现 {len(video_files)} 个视频文件")
        
        # 记录发现的视频文件
        for i, video_file in enumerate(video_files, 1):
            logger.info(f"  {i}. {video_file}")
        
        # 后台处理发现的视频
        for video_file in video_files:
            background_tasks.add_task(scanner.process_new_video, video_file)
        
        return {
            "message": f"扫描完成，发现 {len(video_files)} 个新视频",
            "video_count": len(video_files),
            "video_files": [os.path.basename(f) for f in video_files],
            "scan_directory": str(settings.LOCAL_VIDEO_DIR)
        }
    except Exception as e:
        logger.error(f"扫描本地视频失败: {e}")
        raise HTTPException(status_code=500, detail=f"扫描失败: {str(e)}")

@router.post("/start-watching")
async def start_watching():
    """开始监控本地视频文件夹"""
    try:
        scanner = get_scanner(settings.LOCAL_VIDEO_DIR)
        if not scanner:
            raise HTTPException(status_code=500, detail="视频扫描器初始化失败")
        
        scanner.start_watching()
        
        return {
            "message": "文件夹监控已启动",
            "watch_directory": str(settings.LOCAL_VIDEO_DIR)
        }
    except Exception as e:
        logger.error(f"启动文件夹监控失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动监控失败: {str(e)}")

@router.post("/stop-watching")
async def stop_watching():
    """停止监控本地视频文件夹"""
    try:
        scanner = get_scanner()
        if scanner:
            scanner.stop_watching()
        
        return {"message": "文件夹监控已停止"}
    except Exception as e:
        logger.error(f"停止文件夹监控失败: {e}")
        raise HTTPException(status_code=500, detail=f"停止监控失败: {str(e)}")

@router.get("/list")
async def list_local_videos(db: Session = Depends(get_db)):
    """获取本地视频文件列表（与数据库状态同步）"""
    try:
        watch_dir = Path(settings.LOCAL_VIDEO_DIR)
        if not watch_dir.exists():
            return {"videos": [], "message": "监控目录不存在"}
        
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', '.m4v'}
        videos = []
        
        # 获取数据库中的视频记录
        db_videos = {}
        for video in db.query(Video).filter(Video.platform == "local").all():
            if video.local_path:
                file_name = Path(video.local_path).name
                db_videos[file_name] = {
                    "id": video.id,
                    "status": video.status,
                    "title": video.title,
                    "url": video.url
                }
        
        for file_path in watch_dir.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in video_extensions:
                stat = file_path.stat()
                file_name = file_path.name
                
                # 从数据库获取状态信息
                db_info = db_videos.get(file_name, {})
                processing_status = "unprocessed"
                if db_info:
                    # 映射数据库状态到前端状态
                    status_mapping = {
                        "pending": "unprocessed",
                        "processing": "processing", 
                        "completed": "completed",
                        "failed": "failed"
                    }
                    processing_status = status_mapping.get(db_info["status"], "unprocessed")
                
                videos.append({
                    "name": file_name,
                    "title": db_info.get("title", file_path.stem),
                    "path": str(file_path),
                    "size": stat.st_size,
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "modified_time": stat.st_mtime,
                    "extension": file_path.suffix.lower(),
                    "relative_path": str(file_path.relative_to(watch_dir)),
                    "processing_status": processing_status,
                    "progress": 100 if processing_status == "completed" else (None if processing_status == "processing" else 0),
                    "estimated_time": None,
                    "video_id": db_info.get("id"),
                    "db_status": db_info.get("status")
                })
        
        # 按修改时间排序（最新的在前）
        videos.sort(key=lambda x: x['modified_time'], reverse=True)
        
        return {
            "videos": videos,
            "total_count": len(videos),
            "watch_directory": str(settings.LOCAL_VIDEO_DIR)
        }
    except Exception as e:
        logger.error(f"获取本地视频列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取视频列表失败: {str(e)}")

@router.get("/status")
async def get_scan_status():
    """获取扫描状态"""
    try:
        scanner = get_scanner()
        watch_dir = Path(settings.LOCAL_VIDEO_DIR)
        
        return {
            "watch_directory": str(settings.LOCAL_VIDEO_DIR),
            "directory_exists": watch_dir.exists(),
            "is_watching": scanner is not None and scanner.observer and scanner.observer.is_alive() if scanner else False,
            "processed_count": len(scanner.processed_files) if scanner else 0
        }
    except Exception as e:
        logger.error(f"获取扫描状态失败: {e}")
        return {
            "watch_directory": str(settings.LOCAL_VIDEO_DIR),
            "directory_exists": False,
            "is_watching": False,
            "processed_count": 0,
            "error": str(e)
        }

@router.post("/process/{video_name}")
async def process_local_video(video_name: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """处理指定的本地视频"""
    try:
        watch_dir = Path(settings.LOCAL_VIDEO_DIR)
        video_file = None
        
        # 查找视频文件
        for file_path in watch_dir.rglob('*'):
            if file_path.name == video_name:
                video_file = file_path
                break
        
        if not video_file:
            raise HTTPException(status_code=404, detail="视频文件不存在")
        
        logger.info(f"开始处理视频: {video_name}, 路径: {video_file}")
        
        # 先检查数据库中是否已存在记录
        video_record = db.query(Video).filter(Video.local_path == str(video_file)).first()
        
        if not video_record:
            # 创建新的视频记录
            file_stat = video_file.stat()
            video_record = Video(
                title=video_file.stem,  # 文件名（不含扩展名）
                url=f"local://{video_name}",
                platform="local",
                local_path=str(video_file),
                file_size=file_stat.st_size,
                status="pending"
            )
            db.add(video_record)
            db.commit()
            db.refresh(video_record)
            logger.info(f"已创建视频记录: ID={video_record.id}")
        else:
            # 更新为处理状态
            video_record.status = "pending"
            db.commit()
            logger.info(f"已更新视频记录状态: ID={video_record.id}")
        
        # 添加到后台处理队列
        background_tasks.add_task(process_video_task, str(video_file), video_record.id)
        
        return {
            "message": f"视频 {video_name} 已加入处理队列",
            "video_name": video_name,
            "video_id": video_record.id,
            "status": "pending"
        }
    except Exception as e:
        logger.error(f"处理本地视频失败: {e}")
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")

async def process_video_task(video_path: str, video_id: int = None):
    """后台视频处理任务"""
    try:
        from app.services.ai_service import ai_service
        from app.core.database import SessionLocal, Video, Transcript
        from pathlib import Path
        import time
        
        logger.info(f"🎬 开始处理视频: {video_path} (ID: {video_id})")
        
        # 查找对应的视频记录
        db = SessionLocal()
        try:
            if video_id:
                video = db.query(Video).filter(Video.id == video_id).first()
            else:
                video = db.query(Video).filter(Video.local_path == video_path).first()
            
            if not video:
                logger.error(f"❌ 未找到视频记录: {video_path} (ID: {video_id})")
                return
            
            # 更新状态为处理中
            logger.info(f"📝 更新状态为处理中: {video.title}")
            video.status = "processing"
            db.commit()
            
            # 使用AI服务进行真实的字幕提取
            logger.info(f"🤖 正在使用Whisper处理视频: {video_path}")
            logger.info(f"📊 视频信息: 文件大小 {video.file_size / (1024*1024):.1f}MB")
            start_time = time.time()
            
            # 直接对视频文件进行转录
            transcript_data = await ai_service.transcribe_video(video_path)
            
            processing_time = int(time.time() - start_time)
            logger.info(f"✅ 字幕提取完成，耗时 {processing_time} 秒")
            logger.info(f"📝 转录结果长度: {len(transcript_data.get('original_text', '')) if transcript_data else 0} 字符")
            
            # 删除已存在的字幕记录（如果有）
            existing_transcript = db.query(Transcript).filter(Transcript.video_id == video.id).first()
            if existing_transcript:
                db.delete(existing_transcript)
            
            # 创建新的字幕记录
            transcript = Transcript(
                video_id=video.id,
                original_text=transcript_data.get("original_text", ""),
                cleaned_text=transcript_data.get("cleaned_text", transcript_data.get("original_text", "")),
                summary=transcript_data.get("summary", ""),
                tags=transcript_data.get("tags", ""),
                language=transcript_data.get("language", "zh"),
                confidence_score=transcript_data.get("confidence_score", 0.0),
                processing_time=processing_time
            )
            db.add(transcript)
            
            # 更新为完成状态
            video.status = "completed"
            db.commit()
            logger.info(f"视频处理完成: {video_path}")
            
        except Exception as e:
            logger.error(f"处理视频失败: {video_path}, 错误: {e}")
            # 更新为失败状态
            if 'video' in locals():
                video.status = "failed"
                db.commit()
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"视频处理失败: {video_path}, 错误: {e}")

@router.get("/processing-status")
async def get_processing_status(db: Session = Depends(get_db)):
    """获取所有视频的处理状态"""
    try:
        # 获取各种状态的视频数量和详情
        processing_videos = db.query(Video).filter(
            Video.platform == "local",
            Video.status == "processing"
        ).all()
        
        pending_videos = db.query(Video).filter(
            Video.platform == "local", 
            Video.status == "pending"
        ).all()
        
        completed_count = db.query(Video).filter(
            Video.platform == "local",
            Video.status == "completed"
        ).count()
        
        failed_count = db.query(Video).filter(
            Video.platform == "local",
            Video.status == "failed"
        ).count()
        
        processing_details = []
        for video in processing_videos:
            processing_details.append({
                "id": video.id,
                "title": video.title,
                "file_size_mb": round(video.file_size / (1024*1024), 2) if video.file_size else 0,
                "updated_at": video.updated_at,
                "local_path": Path(video.local_path).name if video.local_path else ""
            })
        
        pending_details = []
        for video in pending_videos:
            pending_details.append({
                "id": video.id,
                "title": video.title,
                "file_size_mb": round(video.file_size / (1024*1024), 2) if video.file_size else 0,
                "created_at": video.created_at,
                "local_path": Path(video.local_path).name if video.local_path else ""
            })
        
        return {
            "processing_videos": processing_details,
            "pending_videos": pending_details,
            "processing_count": len(processing_videos),
            "pending_count": len(pending_videos),
            "completed_count": completed_count,
            "failed_count": failed_count,
            "total_local_videos": completed_count + failed_count + len(processing_videos) + len(pending_videos)
        }
    except Exception as e:
        logger.error(f"获取处理状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")

@router.delete("/delete/{video_name}")
async def delete_local_video(video_name: str):
    """删除本地视频文件"""
    try:
        watch_dir = Path(settings.LOCAL_VIDEO_DIR)
        video_file = None
        
        # 查找视频文件
        for file_path in watch_dir.rglob('*'):
            if file_path.name == video_name:
                video_file = file_path
                break
        
        if not video_file:
            raise HTTPException(status_code=404, detail="视频文件不存在")
        
        # 删除文件
        video_file.unlink()
        logger.info(f"已删除本地视频文件: {video_file}")
        
        return {
            "message": f"视频文件 {video_name} 删除成功",
            "deleted_file": str(video_file)
        }
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="文件不存在")
    except PermissionError:
        raise HTTPException(status_code=403, detail="没有删除权限")
    except Exception as e:
        logger.error(f"删除本地视频失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

@router.get("/file/{file_name}")
async def serve_video_file(file_name: str):
    """提供本地视频文件的HTTP访问"""
    try:
        watch_dir = Path(settings.LOCAL_VIDEO_DIR)
        video_file = None
        
        # 查找视频文件
        for file_path in watch_dir.rglob('*'):
            if file_path.name == file_name:
                video_file = file_path
                break
        
        if not video_file or not video_file.exists():
            raise HTTPException(status_code=404, detail="视频文件不存在")
        
        # 检查文件类型
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', '.m4v'}
        if video_file.suffix.lower() not in video_extensions:
            raise HTTPException(status_code=400, detail="不支持的文件类型")
        
        # 返回文件
        return FileResponse(
            path=str(video_file),
            media_type="video/mp4",
            filename=video_file.name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提供视频文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件服务失败: {str(e)}")

@router.get("/video-detail/{video_id}")
async def get_video_detail(video_id: int, db: Session = Depends(get_db)):
    """获取视频处理详情"""
    try:
        # 查找视频记录
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="视频不存在")
        
        # 查找字幕记录
        transcript = db.query(Transcript).filter(Transcript.video_id == video_id).first()
        
        return {
            "video": {
                "id": video.id,
                "title": video.title,
                "platform": video.platform,
                "status": video.status,
                "url": video.url,
                "local_path": video.local_path,
                "file_fingerprint": video.file_fingerprint,
                "duration": video.duration,
                "file_size": video.file_size,
                "created_at": video.created_at,
                "updated_at": video.updated_at
            },
            "transcript": {
                "id": transcript.id if transcript else None,
                "original_text": transcript.original_text if transcript else None,
                "cleaned_text": transcript.cleaned_text if transcript else None,
                "summary": transcript.summary if transcript else None,
                "tags": transcript.tags if transcript else None,
                "language": transcript.language if transcript else None,
                "confidence_score": transcript.confidence_score if transcript else None,
                "processing_time": transcript.processing_time if transcript else None,
                "created_at": transcript.created_at if transcript else None
            } if transcript else None,
            "has_transcript": transcript is not None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取视频详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取视频详情失败: {str(e)}")