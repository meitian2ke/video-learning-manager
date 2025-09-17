from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from pathlib import Path
from app.core.database import get_db, Video, LearningRecord, Transcript
from app.models.schemas import (
    VideoCreate, VideoUpdate, VideoResponse, VideoDetailResponse,
    VideoListResponse, VideoProcessRequest, LearningRecordCreate
)
from pydantic import BaseModel
from app.services.ai_service import ai_service
import asyncio
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class BatchDeleteRequest(BaseModel):
    video_ids: List[int]

@router.post("/process", response_model=dict)
async def process_video(
    request: VideoProcessRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """处理视频：下载、提取字幕、创建学习记录"""
    
    # 检查URL是否已存在
    existing_video = db.query(Video).filter(Video.url == str(request.url)).first()
    if existing_video:
        raise HTTPException(status_code=400, detail="视频链接已存在")
    
    # 创建视频记录
    video = Video(
        url=str(request.url),
        platform=ai_service._detect_platform(str(request.url)),
        status="pending"
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    
    # 创建学习记录
    learning_record = LearningRecord(
        video_id=video.id,
        priority=request.priority or 3
    )
    db.add(learning_record)
    db.commit()
    
    # 后台处理视频
    background_tasks.add_task(process_video_background, video.id, str(request.url), db)
    
    return {
        "message": "视频处理已开始",
        "video_id": video.id,
        "status": "processing"
    }

async def process_video_background(video_id: int, url: str, db: Session):
    """后台处理视频的具体逻辑"""
    try:
        # 更新状态为下载中
        video = db.query(Video).filter(Video.id == video_id).first()
        video.status = "downloading"
        db.commit()
        
        # 下载视频
        video_path, video_info = await ai_service.download_video(url, video_id)
        
        # 更新视频信息
        video.title = video_info.get("title")
        video.duration = video_info.get("duration")
        video.thumbnail_url = video_info.get("thumbnail")
        video.local_path = video_path
        video.status = "processing"
        db.commit()
        
        # 提取音频
        audio_path = await ai_service.extract_audio(video_path)
        
        # 转录字幕
        transcript_data = await ai_service.transcribe_audio(audio_path)
        
        # 保存字幕到数据库
        from app.core.database import Transcript
        transcript = Transcript(
            video_id=video_id,
            original_text=transcript_data["original_text"],
            cleaned_text=transcript_data["cleaned_text"],
            summary=transcript_data["summary"],
            tags=transcript_data["tags"],
            language=transcript_data["language"],
            confidence_score=transcript_data["confidence_score"]
        )
        db.add(transcript)
        
        # 更新视频状态为完成
        video.status = "completed"
        db.commit()
        
        # 清理临时文件
        await ai_service.cleanup_files(video_id)
        
    except Exception as e:
        # 更新状态为失败
        video = db.query(Video).filter(Video.id == video_id).first()
        if video:
            video.status = "failed"
            db.commit()
        
        print(f"处理视频失败: {e}")

async def process_local_video_background(video_id: int, video_path: str, db: Session):
    """后台处理本地视频的具体逻辑"""
    try:
        # 更新状态为处理中
        video = db.query(Video).filter(Video.id == video_id).first()
        video.status = "processing"
        db.commit()
        
        # 直接转录本地视频
        transcript_data = await ai_service.transcribe_video(video_path)
        
        # 保存字幕到数据库
        from app.core.database import Transcript
        transcript = Transcript(
            video_id=video_id,
            original_text=transcript_data["original_text"],
            cleaned_text=transcript_data["cleaned_text"],
            summary=transcript_data["summary"],
            tags=transcript_data["tags"],
            language=transcript_data["language"],
            confidence_score=transcript_data["confidence_score"]
        )
        db.add(transcript)
        
        # 更新视频状态为完成
        video.status = "completed"
        db.commit()
        
    except Exception as e:
        # 更新状态为失败
        video = db.query(Video).filter(Video.id == video_id).first()
        if video:
            video.status = "failed"
            db.commit()
        
        print(f"处理本地视频失败: {e}")

@router.get("/", response_model=VideoListResponse)
async def get_videos(
    page: int = 1,
    size: int = 20,
    status: Optional[str] = None,
    platform: Optional[str] = None,
    learning_status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取视频列表"""
    
    # 构建查询
    query = db.query(Video)
    
    if status:
        query = query.filter(Video.status == status)
    
    if platform:
        query = query.filter(Video.platform == platform)
    
    if learning_status:
        query = query.join(LearningRecord).filter(LearningRecord.learning_status == learning_status)
    
    # 分页
    total = query.count()
    videos = query.offset((page - 1) * size).limit(size).all()
    
    # 构建响应
    video_details = []
    for video in videos:
        video_detail = VideoDetailResponse(
            id=video.id,
            url=video.url,
            title=video.title,
            platform=video.platform,
            status=video.status,
            thumbnail_url=video.thumbnail_url,
            duration=video.duration,
            file_size=video.file_size,
            created_at=video.created_at,
            updated_at=video.updated_at,
            transcript=video.transcript,
            learning_record=video.learning_record
        )
        video_details.append(video_detail)
    
    return VideoListResponse(
        items=video_details,
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size
    )

@router.get("/{video_id}", response_model=VideoDetailResponse)
async def get_video(video_id: int, db: Session = Depends(get_db)):
    """获取单个视频详情"""
    
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")
    
    return VideoDetailResponse(
        id=video.id,
        url=video.url,
        title=video.title,
        platform=video.platform,
        status=video.status,
        thumbnail_url=video.thumbnail_url,
        duration=video.duration,
        file_size=video.file_size,
        created_at=video.created_at,
        updated_at=video.updated_at,
        transcript=video.transcript,
        learning_record=video.learning_record
    )

@router.put("/{video_id}", response_model=VideoDetailResponse)
async def update_video(
    video_id: int,
    video_update: VideoUpdate,
    db: Session = Depends(get_db)
):
    """更新视频信息"""
    
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")
    
    # 更新字段
    if video_update.title is not None:
        video.title = video_update.title
    
    db.commit()
    db.refresh(video)
    
    return VideoDetailResponse(
        id=video.id,
        url=video.url,
        title=video.title,
        platform=video.platform,
        status=video.status,
        thumbnail_url=video.thumbnail_url,
        duration=video.duration,
        file_size=video.file_size,
        created_at=video.created_at,
        updated_at=video.updated_at,
        transcript=video.transcript,
        learning_record=video.learning_record
    )

@router.delete("/{video_id}")
async def delete_video(video_id: int, db: Session = Depends(get_db)):
    """删除视频"""
    
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")
    
    try:
        # 先删除相关的学习记录
        learning_records = db.query(LearningRecord).filter(LearningRecord.video_id == video_id).all()
        for record in learning_records:
            db.delete(record)
        
        # 删除相关的字幕记录
        transcripts = db.query(Transcript).filter(Transcript.video_id == video_id).all()
        for transcript in transcripts:
            db.delete(transcript)
        
        # 清理文件
        await ai_service.cleanup_files(video_id)
        
        # 最后删除视频记录
        db.delete(video)
        db.commit()
        
        return {"message": "视频删除成功"}
        
    except Exception as e:
        db.rollback()
        logger.error(f"删除视频失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

@router.post("/{video_id}/retry")
async def retry_video_processing(
    video_id: int, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """重新处理失败的视频"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")
    
    if video.status not in ["failed", "pending"]:
        raise HTTPException(status_code=400, detail="只能重新处理失败或待处理的视频")
    
    # 重置状态
    video.status = "pending"
    db.commit()
    
    # 重新处理
    if video.local_path and Path(video.local_path).exists():
        # 本地视频直接转录
        background_tasks.add_task(process_local_video_background, video.id, video.local_path, db)
    else:
        # 在线视频重新下载处理
        background_tasks.add_task(process_video_background, video.id, video.url, db)
    
    return {"message": "视频重新处理已开始", "video_id": video_id}

@router.post("/batch-retry")
async def batch_retry_videos(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """批量重新处理所有失败或待处理的视频"""
    pending_videos = db.query(Video).filter(Video.status.in_(["failed", "pending"])).all()
    
    retry_count = 0
    for video in pending_videos:
        video.status = "pending" 
        if video.local_path and Path(video.local_path).exists():
            background_tasks.add_task(process_local_video_background, video.id, video.local_path, db)
        else:
            background_tasks.add_task(process_video_background, video.id, video.url, db)
        retry_count += 1
    
    db.commit()
    
    return {
        "message": f"批量重新处理已开始",
        "retry_count": retry_count
    }

@router.post("/batch-delete")
async def batch_delete_videos(request: BatchDeleteRequest, db: Session = Depends(get_db)):
    """批量删除视频"""
    
    deleted_count = 0
    failed_count = 0
    failed_videos = []
    
    for video_id in request.video_ids:
        try:
            video = db.query(Video).filter(Video.id == video_id).first()
            if not video:
                failed_count += 1
                failed_videos.append({"id": video_id, "error": "视频不存在"})
                continue
            
            # 先删除相关的学习记录
            learning_records = db.query(LearningRecord).filter(LearningRecord.video_id == video_id).all()
            for record in learning_records:
                db.delete(record)
            
            # 删除相关的字幕记录
            transcripts = db.query(Transcript).filter(Transcript.video_id == video_id).all()
            for transcript in transcripts:
                db.delete(transcript)
            
            # 清理文件
            try:
                await ai_service.cleanup_files(video_id)
            except Exception as cleanup_error:
                logger.warning(f"清理文件失败 (视频ID: {video_id}): {cleanup_error}")
            
            # 最后删除视频记录
            db.delete(video)
            deleted_count += 1
            
        except Exception as e:
            failed_count += 1
            failed_videos.append({"id": video_id, "error": str(e)})
            logger.error(f"删除视频 {video_id} 失败: {e}")
    
    try:
        db.commit()
        return {
            "message": f"批量删除完成",
            "deleted_count": deleted_count,
            "failed_count": failed_count,
            "failed_videos": failed_videos,
            "total_requested": len(request.video_ids)
        }
    except Exception as e:
        db.rollback()
        logger.error(f"批量删除提交失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量删除失败: {str(e)}")