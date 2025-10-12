"""
视频处理Celery任务
每个Worker进程独立管理GPU资源，避免内存泄漏和竞争
"""

import asyncio
import logging
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from celery import current_task
from app.celery_app import celery_app
from app.core.database import SessionLocal, Video, Transcript

logger = logging.getLogger(__name__)

# 全局变量：每个Worker进程的AI服务实例
_worker_ai_service = None

def get_worker_ai_service():
    """获取当前Worker进程的AI服务实例（单例模式）"""
    global _worker_ai_service
    if _worker_ai_service is None:
        from app.services.ai_service import AITranscriptionService
        logger.info("🤖 初始化Worker进程的AI服务")
        _worker_ai_service = AITranscriptionService()
        logger.info("✅ AI服务初始化完成")
    return _worker_ai_service

@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def process_video_task(self, video_id: int):
    """
    处理单个视频的Celery任务
    
    Args:
        self: Celery任务实例
        video_id: 要处理的视频ID
    
    Returns:
        dict: 处理结果
    """
    task_id = self.request.id
    db = SessionLocal()
    
    try:
        logger.info(f"🎬 开始处理视频任务: video_id={video_id}, task_id={task_id}")
        
        # 1. 获取视频信息
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise Exception(f"视频不存在: video_id={video_id}")
        
        logger.info(f"📹 视频信息: {video.title}, 路径: {video.local_path}")
        
        # 2. 检查文件是否存在
        if not video.local_path or not Path(video.local_path).exists():
            raise Exception(f"视频文件不存在: {video.local_path}")
        
        # 3. 过滤macOS垃圾文件
        if Path(video.local_path).name.startswith('._'):
            logger.warning(f"⚠️ 跳过macOS元数据文件: {video.local_path}")
            video.status = "failed"
            db.commit()
            return {"status": "skipped", "reason": "macOS metadata file"}
        
        # 4. 更新状态为处理中
        video.status = "processing"
        video.task_id = task_id
        video.updated_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"📝 更新视频状态为处理中: {video.title}")
        
        # 5. 获取Worker进程的AI服务
        ai_service = get_worker_ai_service()
        
        # 6. 开始处理视频
        start_time = time.time()
        logger.info(f"🚀 开始转录视频: {video.local_path}")
        
        # 更新任务进度
        self.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': 100, 'status': '正在转录音频...'}
        )
        
        # 实际转录处理
        result = asyncio.run(ai_service.transcribe_video(video.local_path))
        
        processing_time = int(time.time() - start_time)
        logger.info(f"✅ 转录完成，耗时: {processing_time}秒")
        
        # 7. 删除已存在的字幕记录（如果有）
        existing_transcript = db.query(Transcript).filter(Transcript.video_id == video_id).first()
        if existing_transcript:
            db.delete(existing_transcript)
            logger.info("🗑️ 删除了已存在的字幕记录")
        
        # 8. 创建新的字幕记录
        transcript = Transcript(
            video_id=video_id,
            original_text=result.get("original_text", ""),
            cleaned_text=result.get("cleaned_text", result.get("original_text", "")),
            summary=result.get("summary", ""),
            tags=result.get("tags", ""),
            language=result.get("language", "zh"),
            confidence_score=result.get("confidence_score", 0.0),
            processing_time=processing_time
        )
        db.add(transcript)
        
        # 9. 更新视频状态为完成
        video.status = "completed"
        video.updated_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"🎉 视频处理完成: {video.title}")
        
        # 10. 清理GPU内存（但保留模型）
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                logger.debug("🧹 GPU缓存已清理")
        except Exception as e:
            logger.warning(f"⚠️ GPU缓存清理失败: {e}")
        
        return {
            "status": "success", 
            "video_id": video_id,
            "processing_time": processing_time,
            "transcript_length": len(result.get("original_text", "")),
            "language": result.get("language", "unknown")
        }
        
    except Exception as exc:
        logger.error(f"❌ 视频处理失败: video_id={video_id}, 错误: {exc}")
        logger.error(f"📋 错误堆栈:\n{traceback.format_exc()}")
        
        # 更新数据库状态
        try:
            video = db.query(Video).filter(Video.id == video_id).first()
            if video:
                video.retry_count = (video.retry_count or 0) + 1
                
                # 判断是否需要重试
                if self.request.retries < self.max_retries:
                    video.status = "pending"  # 重新排队
                    db.commit()
                    
                    retry_delay = min(300 * (self.request.retries + 1), 1800)  # 递增延迟，最长30分钟
                    logger.info(f"🔄 准备重试 ({self.request.retries + 1}/{self.max_retries})，延迟{retry_delay}秒")
                    
                    raise self.retry(countdown=retry_delay, exc=exc)
                else:
                    video.status = "failed"
                    db.commit()
                    logger.error(f"🚫 重试次数用完，标记为失败: {video.title}")
        except Exception as db_exc:
            logger.error(f"❌ 更新数据库状态失败: {db_exc}")
        
        return {
            "status": "failed", 
            "video_id": video_id,
            "error": str(exc),
            "retries": self.request.retries
        }
    
    finally:
        db.close()

@celery_app.task
def batch_process_videos(video_ids: list):
    """
    批量处理视频任务
    
    Args:
        video_ids: 视频ID列表
    
    Returns:
        dict: 批量处理结果
    """
    logger.info(f"📦 开始批量处理 {len(video_ids)} 个视频")
    
    results = []
    for video_id in video_ids:
        try:
            # 提交单个视频处理任务
            task = process_video_task.delay(video_id)
            results.append({
                "video_id": video_id,
                "task_id": task.id,
                "status": "submitted"
            })
        except Exception as e:
            logger.error(f"❌ 提交视频任务失败: video_id={video_id}, 错误: {e}")
            results.append({
                "video_id": video_id,
                "status": "submit_failed",
                "error": str(e)
            })
    
    logger.info(f"✅ 批量提交完成，成功: {sum(1 for r in results if r['status'] == 'submitted')} 个")
    
    return {
        "total": len(video_ids),
        "submitted": sum(1 for r in results if r['status'] == 'submitted'),
        "failed": sum(1 for r in results if r['status'] == 'submit_failed'),
        "results": results
    }

@celery_app.task
def get_task_status(task_id: str):
    """
    获取任务状态
    
    Args:
        task_id: Celery任务ID
    
    Returns:
        dict: 任务状态信息
    """
    from celery.result import AsyncResult
    
    result = AsyncResult(task_id, app=celery_app)
    
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result,
        "traceback": result.traceback
    }

@celery_app.task
def cleanup_failed_tasks():
    """
    清理失败的任务，重置为待处理状态
    """
    db = SessionLocal()
    try:
        failed_videos = db.query(Video).filter(
            Video.status == "processing",
            Video.updated_at < datetime.utcnow() - timedelta(hours=2)  # 超过2小时的处理中任务
        ).all()
        
        reset_count = 0
        for video in failed_videos:
            video.status = "pending"
            video.task_id = None
            reset_count += 1
        
        db.commit()
        
        logger.info(f"🧹 清理了 {reset_count} 个卡住的任务")
        return {"reset_count": reset_count}
        
    except Exception as e:
        logger.error(f"❌ 清理失败任务出错: {e}")
        return {"error": str(e)}
    finally:
        db.close()