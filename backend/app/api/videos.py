from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db, Video, LearningRecord
from app.models.schemas import (
    VideoCreate, VideoUpdate, VideoResponse, VideoDetailResponse,
    VideoListResponse, VideoProcessRequest, LearningRecordCreate
)
from app.services.ai_service import ai_service
import asyncio

router = APIRouter()

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
    
    # 清理文件
    await ai_service.cleanup_files(video_id)
    
    # 删除数据库记录
    db.delete(video)
    db.commit()
    
    return {"message": "视频删除成功"}