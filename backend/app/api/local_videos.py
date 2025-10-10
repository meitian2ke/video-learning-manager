"""
本地视频管理API
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from typing import List, Dict, Any
import logging
import traceback
import torch
from pathlib import Path
from datetime import datetime, timedelta

from app.core.config import settings
from app.services.local_video_scanner import get_scanner
from app.core.database import get_db, Video, Transcript, SessionLocal
from sqlalchemy.orm import Session
from fastapi import Depends
import os

# 导入Celery相关
from app.tasks.video_tasks import process_video_task, batch_process_videos, get_task_status

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
        logger.info("开始获取本地视频列表")
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
            if (file_path.is_file() and 
                file_path.suffix.lower() in video_extensions and
                not file_path.name.startswith('._') and  # 过滤macOS元数据文件
                not file_path.name.startswith('.DS_Store')):
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
        import traceback
        error_detail = f"获取本地视频列表失败: {str(e)}"
        logger.error(f"{error_detail}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_detail)

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

@router.post("/debug-process/{video_name}")
async def debug_process_video(video_name: str, db: Session = Depends(get_db)):
    """Debug模式处理视频 - 返回详细步骤信息"""
    debug_steps = []
    video_path = None
    
    def add_debug_step(step: str, status: str, message: str, details: Dict[str, Any] = None):
        debug_steps.append({
            "step": step,
            "status": status,  # "success", "error", "running" 
            "message": message,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        })
    
    try:
        # 步骤1: 文件定位
        add_debug_step("1_file_location", "running", "正在定位视频文件...")
        
        watch_dir = Path(settings.LOCAL_VIDEO_DIR)
        video_file = None
        
        for file_path in watch_dir.rglob('*'):
            if file_path.name == video_name:
                video_file = file_path
                break
        
        if not video_file:
            add_debug_step("1_file_location", "error", f"视频文件不存在: {video_name}")
            return {"video_name": video_name, "debug_steps": debug_steps}
        
        video_path = str(video_file)
        file_size = video_file.stat().st_size
        add_debug_step("1_file_location", "success", f"找到视频文件: {video_path}", {
            "file_size": file_size,
            "file_size_mb": round(file_size / 1024 / 1024, 2)
        })
        
        # 步骤2: 系统环境检查
        add_debug_step("2_system_check", "running", "检查系统环境...")
        
        system_info = {
            "cuda_available": torch.cuda.is_available(),
            "gpu_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
            "environment": settings.ENVIRONMENT,
            "whisper_model": settings.WHISPER_MODEL,
            "whisper_device": settings.WHISPER_DEVICE
        }
        
        if torch.cuda.is_available():
            system_info["gpu_name"] = torch.cuda.get_device_name(0)
            system_info["gpu_memory_allocated"] = torch.cuda.memory_allocated()
            system_info["gpu_memory_reserved"] = torch.cuda.memory_reserved()
        
        add_debug_step("2_system_check", "success", "系统环境检查完成", system_info)
        
        # 步骤3: 模型加载测试
        add_debug_step("3_model_loading", "running", "测试模型加载...")
        
        from app.services.ai_service import ai_service
        
        try:
            # 检查模型路径/名称
            model_path_or_name = ai_service._get_model_path_or_name()
            model_details = {
                "model_path_or_name": model_path_or_name,
                "is_local_path": model_path_or_name.startswith("/"),
                "device": ai_service._choose_device(),
                "compute_type": ai_service._choose_compute_type()
            }
            
            # 如果是本地路径，检查文件是否存在
            if model_path_or_name.startswith("/"):
                model_details["path_exists"] = Path(model_path_or_name).exists()
            
            # 尝试加载模型
            ai_service._ensure_model_loaded()
            model_details["model_loaded"] = ai_service.model is not None
            model_details["model_type"] = type(ai_service.model).__name__ if ai_service.model else None
            
            add_debug_step("3_model_loading", "success", "模型加载成功", model_details)
            
        except Exception as e:
            add_debug_step("3_model_loading", "error", f"模型加载失败: {str(e)}", {
                "error": str(e),
                "traceback": traceback.format_exc()
            })
            return {"video_name": video_name, "video_path": video_path, "debug_steps": debug_steps}
        
        # 步骤4: 视频处理测试
        add_debug_step("4_video_processing", "running", "开始视频处理...")
        
        try:
            result = await ai_service.transcribe_video(video_path)
            
            processing_details = {
                "transcription_length": len(result.get("original_text", "")),
                "language": result.get("language", "unknown"),
                "confidence_score": result.get("confidence_score", 0),
                "segments_count": len(result.get("segments", [])),
                "has_summary": bool(result.get("summary")),
                "has_tags": bool(result.get("tags"))
            }
            
            add_debug_step("4_video_processing", "success", "视频处理完成", processing_details)
            
            return {
                "video_name": video_name,
                "video_path": video_path,
                "debug_steps": debug_steps,
                "result": {
                    "original_text": result.get("original_text", "")[:200] + "..." if len(result.get("original_text", "")) > 200 else result.get("original_text", ""),
                    "summary": result.get("summary", ""),
                    "language": result.get("language", "unknown"),
                    "confidence_score": result.get("confidence_score", 0)
                }
            }
            
        except Exception as e:
            add_debug_step("4_video_processing", "error", f"视频处理失败: {str(e)}", {
                "error": str(e),
                "traceback": traceback.format_exc()
            })
            return {"video_name": video_name, "video_path": video_path, "debug_steps": debug_steps}
            
    except Exception as e:
        add_debug_step("system_error", "error", f"系统错误: {str(e)}", {
            "error": str(e),
            "traceback": traceback.format_exc()
        })
        return {"video_name": video_name, "video_path": video_path, "debug_steps": debug_steps}

@router.post("/process/{video_name}")
async def process_local_video(video_name: str, db: Session = Depends(get_db)):
    """提交指定的本地视频到Celery队列处理"""
    try:
        logger.info(f"📤 提交视频处理请求: {video_name}")
        
        # 查找视频文件
        watch_dir = Path(settings.LOCAL_VIDEO_DIR)
        video_file = None
        
        for file_path in watch_dir.rglob('*'):
            if file_path.name == video_name:
                video_file = file_path
                break
        
        if not video_file:
            raise HTTPException(status_code=404, detail="视频文件不存在")
        
        # 过滤macOS垃圾文件
        if video_file.name.startswith('._'):
            raise HTTPException(status_code=400, detail="不能处理macOS元数据文件")
        
        logger.info(f"📹 找到视频文件: {video_file}")
        
        # 检查数据库中是否已存在记录
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
                status="pending",
                retry_count=0
            )
            db.add(video_record)
            db.commit()
            db.refresh(video_record)
            logger.info(f"✅ 创建视频记录: ID={video_record.id}")
        else:
            # 更新状态为待处理
            video_record.status = "pending"
            video_record.retry_count = 0
            video_record.task_id = None
            db.commit()
            logger.info(f"🔄 重置视频记录状态: ID={video_record.id}")
        
        # 提交到Celery队列
        task = process_video_task.delay(video_record.id)
        
        # 更新任务ID
        video_record.task_id = task.id
        db.commit()
        
        logger.info(f"🚀 视频已提交到Celery队列: task_id={task.id}")
        
        return {
            "message": f"视频 {video_name} 已提交到处理队列",
            "video_name": video_name,
            "video_id": video_record.id,
            "task_id": task.id,
            "status": "pending"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 提交视频处理失败: {video_name}, 错误: {e}")
        logger.error(f"📋 错误堆栈:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"提交处理失败: {str(e)}")

@router.get("/model-status")
async def get_model_status():
    """获取模型状态信息"""
    try:
        from app.services.ai_service import ai_service
        
        status_info = {
            "model_name": settings.WHISPER_MODEL,
            "device": ai_service._choose_device(),
            "compute_type": ai_service._choose_compute_type(),
            "environment": ai_service.environment,
            "model_loaded": ai_service.model is not None,
            "cuda_available": torch.cuda.is_available(),
            "gpu_count": torch.cuda.device_count() if torch.cuda.is_available() else 0
        }
        
        # 尝试获取模型路径信息
        try:
            model_path_or_name = ai_service._get_model_path_or_name()
            status_info["model_path_or_name"] = model_path_or_name
            
            if model_path_or_name.startswith("/"):
                status_info["is_local_model"] = True
                status_info["model_path_exists"] = Path(model_path_or_name).exists()
            else:
                status_info["is_local_model"] = False
        except Exception as e:
            status_info["model_path_error"] = str(e)
        
        # GPU信息
        if torch.cuda.is_available():
            status_info["gpu_info"] = {
                "gpu_name": torch.cuda.get_device_name(0),
                "memory_allocated_mb": round(torch.cuda.memory_allocated() / 1024 / 1024, 2),
                "memory_reserved_mb": round(torch.cuda.memory_reserved() / 1024 / 1024, 2)
            }
        
        return status_info
        
    except Exception as e:
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }

# 旧的process_video_task函数已移至app.tasks.video_tasks模块

@router.get("/processing-status")
async def get_processing_status(db: Session = Depends(get_db)):
    """获取所有视频的处理状态"""
    try:
        # 获取各种状态的视频数量和详情
        processing_videos = db.query(Video).filter(
            Video.status.in_(["processing", "pending"])
        ).all()
        
        return {
            "processing_count": len(processing_videos),
            "videos": [{
                "id": v.id,
                "title": v.title,
                "status": v.status
            } for v in processing_videos]
        }
    except Exception as e:
        logger.error(f"获取处理状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/quick-debug/{video_name}")
async def quick_debug_video(video_name: str):
    """快速debug接口 - 只检查基础信息"""
    try:
        # 文件检查
        watch_dir = Path(settings.LOCAL_VIDEO_DIR)
        video_file = None
        
        for file_path in watch_dir.rglob('*'):
            if file_path.name == video_name:
                video_file = file_path
                break
        
        if not video_file:
            return {"error": f"视频文件不存在: {video_name}"}
        
        # 基础信息
        file_size = video_file.stat().st_size
        
        # 模型状态快速检查
        from app.services.ai_service import ai_service
        
        quick_info = {
            "video_found": True,
            "video_path": str(video_file),
            "file_size_mb": round(file_size / 1024 / 1024, 2),
            "cuda_available": torch.cuda.is_available(),
            "model_loaded": ai_service.model is not None,
            "whisper_device": settings.WHISPER_DEVICE,
            "whisper_model": settings.WHISPER_MODEL
        }
        
        return quick_info
        
    except Exception as e:
        return {
            "error": str(e),
            "video_name": video_name
        }

@router.post("/deep-debug/{video_name}")
async def deep_debug_whisper(video_name: str):
    """深度debug faster-whisper音频维度问题"""
    try:
        from app.services.ai_service import ai_service
        import torch
        from pathlib import Path
        
        # 文件检查
        watch_dir = Path(settings.LOCAL_VIDEO_DIR)
        video_file = None
        for file_path in watch_dir.rglob('*'):
            if file_path.name == video_name:
                video_file = file_path
                break
        
        if not video_file:
            return {"error": f"视频文件不存在: {video_name}"}
        
        video_path = str(video_file)
        debug_info = {
            "video_file": video_path,
            "file_size_mb": round(video_file.stat().st_size / 1024 / 1024, 2),
            "steps": []
        }
        
        # 步骤1: 检查模型状态
        debug_info["steps"].append({
            "step": "model_check",
            "model_loaded": ai_service.model is not None,
            "device": ai_service._choose_device(),
            "compute_type": ai_service._choose_compute_type()
        })
        
        # 步骤2: 尝试加载模型
        try:
            ai_service._ensure_model_loaded()
            debug_info["steps"].append({
                "step": "model_loaded",
                "status": "success",
                "model_type": type(ai_service.model).__name__
            })
        except Exception as e:
            debug_info["steps"].append({
                "step": "model_load_failed",
                "status": "error",
                "error": str(e)
            })
            return debug_info
        
        # 步骤3: 测试不同参数的转录
        test_params = [
            {"name": "default", "params": {"language": "zh", "task": "transcribe"}},
            {"name": "auto_detect", "params": {"task": "transcribe"}},
            {"name": "english", "params": {"language": "en", "task": "transcribe"}},
            {"name": "no_language", "params": {"task": "transcribe", "beam_size": 1}}
        ]
        
        for test in test_params:
            try:
                segments, info = ai_service.model.transcribe(video_path, **test["params"])
                
                # 收集一些结果
                segment_count = 0
                first_text = ""
                for segment in segments:
                    segment_count += 1
                    if segment_count == 1:
                        first_text = segment.text[:50]  # 只取前50个字符
                    if segment_count >= 3:  # 只处理前3个片段
                        break
                
                debug_info["steps"].append({
                    "step": f"transcribe_{test['name']}",
                    "status": "success",
                    "params": test["params"],
                    "language_detected": info.language,
                    "confidence": info.language_probability,
                    "duration": info.duration,
                    "segments_processed": segment_count,
                    "first_text": first_text
                })
                
                # 如果成功，直接返回
                return debug_info
                
            except Exception as e:
                debug_info["steps"].append({
                    "step": f"transcribe_{test['name']}",
                    "status": "error",
                    "params": test["params"],
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                continue
        
        return debug_info
        
    except Exception as e:
        return {
            "error": str(e),
            "video_name": video_name,
            "error_type": type(e).__name__
        }

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
                "retry_count": video.retry_count,
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

@router.post("/reset-failed")
async def reset_failed_videos(db: Session = Depends(get_db)):
    """重置所有失败的视频状态，允许重新处理"""
    try:
        # 查找所有失败的本地视频
        failed_videos = db.query(Video).filter(
            Video.platform == "local",
            Video.status == "failed"
        ).all()
        
        reset_count = 0
        for video in failed_videos:
            video.status = "pending"
            video.retry_count = 0  # 重置重试次数
            reset_count += 1
        
        db.commit()
        
        logger.info(f"已重置 {reset_count} 个失败视频的状态")
        
        return {
            "message": f"已重置 {reset_count} 个失败视频，可重新处理",
            "reset_count": reset_count
        }
        
    except Exception as e:
        logger.error(f"重置失败视频状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"重置失败: {str(e)}")

@router.post("/reset-video/{video_name}")
async def reset_single_video(video_name: str, db: Session = Depends(get_db)):
    """重置单个视频的失败状态"""
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
        
        # 查找数据库记录
        video = db.query(Video).filter(Video.local_path == str(video_file)).first()
        if not video:
            raise HTTPException(status_code=404, detail="视频记录不存在")
        
        # 重置状态
        video.status = "pending"
        video.retry_count = 0
        db.commit()
        
        logger.info(f"已重置视频状态: {video_name}")
        
        return {
            "message": f"视频 {video_name} 状态已重置，可重新处理",
            "video_id": video.id,
            "status": "pending"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重置视频状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"重置失败: {str(e)}")

@router.get("/logs")
async def get_processing_logs():
    """获取视频处理日志"""
    try:
        from app.core.config import settings
        import os
        
        # 获取日志文件路径
        log_dir = Path(settings.UPLOAD_DIR).parent / "logs"
        log_file = log_dir / "video_processing.log"
        
        if not log_file.exists():
            return {
                "logs": [],
                "message": "暂无处理日志"
            }
        
        # 读取最新的100行日志
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            recent_logs = lines[-100:] if len(lines) > 100 else lines
        
        return {
            "logs": [line.strip() for line in recent_logs],
            "total_lines": len(lines),
            "showing_recent": len(recent_logs)
        }
        
    except Exception as e:
        logger.error(f"获取处理日志失败: {e}")
        return {
            "logs": [f"获取日志失败: {str(e)}"],
            "error": True
        }

@router.get("/logs/live")
async def get_live_logs():
    """获取实时处理日志（最新50行）"""
    try:
        from app.core.config import settings
        
        log_dir = Path(settings.UPLOAD_DIR).parent / "logs"
        log_file = log_dir / "video_processing.log"
        
        if not log_file.exists():
            return {"logs": ["日志文件不存在"]}
        
        # 读取最新的50行
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            recent_logs = lines[-50:] if len(lines) > 50 else lines
        
        return {
            "logs": [line.strip() for line in recent_logs if line.strip()],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取实时日志失败: {e}")
        return {"logs": [f"获取日志失败: {str(e)}"]}

@router.get("/task-status/{task_id}")
async def get_celery_task_status(task_id: str):
    """获取Celery任务状态"""
    try:
        from celery.result import AsyncResult
        from app.celery_app import celery_app
        
        result = AsyncResult(task_id, app=celery_app)
        
        return {
            "task_id": task_id,
            "status": result.status,
            "result": result.result if result.ready() else None,
            "info": result.info,
            "traceback": result.traceback if result.failed() else None
        }
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        return {
            "task_id": task_id,
            "status": "ERROR",
            "error": str(e)
        }

@router.post("/batch-process")
async def batch_process_videos_api(video_names: List[str], db: Session = Depends(get_db)):
    """批量处理视频"""
    try:
        logger.info(f"📦 批量处理请求: {len(video_names)} 个视频")
        
        video_ids = []
        watch_dir = Path(settings.LOCAL_VIDEO_DIR)
        
        # 验证所有视频文件存在并创建记录
        for video_name in video_names:
            # 跳过macOS垃圾文件
            if video_name.startswith('._'):
                logger.warning(f"⚠️ 跳过macOS元数据文件: {video_name}")
                continue
                
            # 查找视频文件
            video_file = None
            for file_path in watch_dir.rglob('*'):
                if file_path.name == video_name:
                    video_file = file_path
                    break
            
            if not video_file:
                logger.warning(f"⚠️ 视频文件不存在: {video_name}")
                continue
            
            # 检查或创建视频记录
            video_record = db.query(Video).filter(Video.local_path == str(video_file)).first()
            
            if not video_record:
                file_stat = video_file.stat()
                video_record = Video(
                    title=video_file.stem,
                    url=f"local://{video_name}",
                    platform="local",
                    local_path=str(video_file),
                    file_size=file_stat.st_size,
                    status="pending",
                    retry_count=0
                )
                db.add(video_record)
                db.flush()  # 获取ID但不提交
            else:
                # 重置状态
                video_record.status = "pending"
                video_record.retry_count = 0
                video_record.task_id = None
            
            video_ids.append(video_record.id)
        
        db.commit()
        
        # 提交批量处理任务
        task = batch_process_videos.delay(video_ids)
        
        logger.info(f"🚀 批量处理任务已提交: task_id={task.id}, 视频数量={len(video_ids)}")
        
        return {
            "message": f"已提交 {len(video_ids)} 个视频到批量处理队列",
            "task_id": task.id,
            "video_count": len(video_ids),
            "skipped_count": len(video_names) - len(video_ids)
        }
        
    except Exception as e:
        logger.error(f"❌ 批量处理提交失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量处理失败: {str(e)}")

@router.get("/queue-status")
async def get_queue_status():
    """获取Celery队列状态"""
    try:
        from app.celery_app import celery_app
        
        inspect = celery_app.control.inspect()
        
        # 获取活跃任务
        active_tasks = inspect.active()
        
        # 获取预定任务
        scheduled_tasks = inspect.scheduled()
        
        # 获取保留任务
        reserved_tasks = inspect.reserved()
        
        return {
            "active_tasks": active_tasks,
            "scheduled_tasks": scheduled_tasks,
            "reserved_tasks": reserved_tasks,
            "worker_stats": inspect.stats()
        }
        
    except Exception as e:
        logger.error(f"获取队列状态失败: {e}")
        return {
            "error": str(e),
            "message": "无法连接到Celery"
        }

@router.get("/debug-system")
async def debug_system_status():
    """调试系统状态 - 检查GPU、模型、队列等"""
    try:
        import torch
        import psutil
        from app.services.ai_service import ai_service
        
        debug_info = {
            "timestamp": datetime.now().isoformat(),
            "system": {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent
            },
            "gpu": {
                "available": torch.cuda.is_available(),
                "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0
            },
            "whisper": {
                "model_loaded": ai_service.model is not None,
                "model_name": settings.WHISPER_MODEL,
                "device": settings.WHISPER_DEVICE,
                "compute_type": settings.WHISPER_COMPUTE_TYPE
            },
            "environment": {
                "transcription_mode": settings.TRANSCRIPTION_MODE,
                "max_concurrent": settings.MAX_CONCURRENT_TRANSCRIPTIONS,
                "queue_size": settings.TRANSCRIPTION_QUEUE_SIZE
            }
        }
        
        # GPU详细信息
        if torch.cuda.is_available():
            debug_info["gpu"].update({
                "name": torch.cuda.get_device_name(0),
                "memory_allocated_mb": round(torch.cuda.memory_allocated() / 1024 / 1024, 2),
                "memory_reserved_mb": round(torch.cuda.memory_reserved() / 1024 / 1024, 2),
                "memory_total_mb": round(torch.cuda.get_device_properties(0).total_memory / 1024 / 1024, 2)
            })
        
        # 检查处理队列状态
        with SessionLocal() as db:
            queue_status = {
                "pending": db.query(Video).filter(Video.status == "pending", Video.platform == "local").count(),
                "processing": db.query(Video).filter(Video.status == "processing", Video.platform == "local").count(),
                "completed": db.query(Video).filter(Video.status == "completed", Video.platform == "local").count(),
                "failed": db.query(Video).filter(Video.status == "failed", Video.platform == "local").count()
            }
            debug_info["queue"] = queue_status
        
        return debug_info
        
    except Exception as e:
        logger.error(f"获取系统调试信息失败: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.post("/force-reset-processing")
async def force_reset_processing(db: Session = Depends(get_db)):
    """强制重置所有处理中状态的视频 - 解决队列卡住问题"""
    try:
        # 查找所有处理中的本地视频
        processing_videos = db.query(Video).filter(
            Video.platform == "local",
            Video.status == "processing"
        ).all()
        
        reset_count = 0
        for video in processing_videos:
            # 检查视频是否真的还在处理中（简单检查：超过30分钟的处理认为是卡住了）
            if video.updated_at:
                time_diff = datetime.utcnow() - video.updated_at
                if time_diff.total_seconds() > 1800:  # 30分钟
                    video.status = "pending"
                    video.retry_count = (video.retry_count or 0) + 1
                    reset_count += 1
                    logger.info(f"强制重置卡住的视频: {video.title} (超时: {time_diff.total_seconds()}秒)")
            else:
                # 没有更新时间的直接重置
                video.status = "pending"
                video.retry_count = (video.retry_count or 0) + 1
                reset_count += 1
                logger.info(f"强制重置无时间戳的视频: {video.title}")
        
        db.commit()
        
        logger.info(f"强制重置了 {reset_count} 个卡住的处理中视频")
        
        return {
            "message": f"已强制重置 {reset_count} 个处理中视频，队列应该恢复正常",
            "reset_count": reset_count,
            "total_processing": len(processing_videos)
        }
        
    except Exception as e:
        logger.error(f"强制重置处理中视频失败: {e}")
        raise HTTPException(status_code=500, detail=f"强制重置失败: {str(e)}")

@router.post("/clear-gpu-memory")
async def clear_gpu_memory():
    """清理GPU内存，释放可能卡住的模型"""
    try:
        import torch
        from app.services.ai_service import ai_service
        
        # 清理GPU缓存
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
            
        # 重新初始化模型
        ai_service.model = None
        
        memory_info = {}
        if torch.cuda.is_available():
            memory_info = {
                "memory_allocated_mb": round(torch.cuda.memory_allocated() / 1024 / 1024, 2),
                "memory_reserved_mb": round(torch.cuda.memory_reserved() / 1024 / 1024, 2),
                "memory_total_mb": round(torch.cuda.get_device_properties(0).total_memory / 1024 / 1024, 2)
            }
        
        logger.info("已清理GPU内存并重置Whisper模型")
        
        return {
            "message": "GPU内存已清理，Whisper模型已重置",
            "gpu_memory": memory_info
        }
        
    except Exception as e:
        logger.error(f"清理GPU内存失败: {e}")
        raise HTTPException(status_code=500, detail=f"清理GPU内存失败: {str(e)}")

@router.get("/check-stuck-videos")
async def check_stuck_videos(db: Session = Depends(get_db)):
    """检查可能卡住的视频"""
    try:
        from datetime import timedelta
        
        # 查找超过30分钟还在处理中的视频
        thirty_minutes_ago = datetime.utcnow() - timedelta(minutes=30)
        
        stuck_videos = db.query(Video).filter(
            Video.platform == "local",
            Video.status == "processing",
            Video.updated_at < thirty_minutes_ago
        ).all()
        
        stuck_info = []
        for video in stuck_videos:
            time_diff = datetime.utcnow() - video.updated_at if video.updated_at else None
            stuck_info.append({
                "id": video.id,
                "title": video.title,
                "local_path": video.local_path,
                "status": video.status,
                "retry_count": video.retry_count or 0,
                "updated_at": video.updated_at.isoformat() if video.updated_at else None,
                "stuck_duration_minutes": int(time_diff.total_seconds() / 60) if time_diff else None
            })
        
        return {
            "stuck_videos": stuck_info,
            "stuck_count": len(stuck_videos),
            "message": f"发现 {len(stuck_videos)} 个可能卡住的视频"
        }
        
    except Exception as e:
        logger.error(f"检查卡住视频失败: {e}")
        raise HTTPException(status_code=500, detail=f"检查失败: {str(e)}")