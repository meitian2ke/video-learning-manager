from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from app.core.database import get_db, LearningRecord, Video
from app.models.schemas import (
    LearningRecordResponse, LearningRecordUpdate, LearningStatsResponse
)

router = APIRouter()

@router.get("/{video_id}", response_model=LearningRecordResponse)
async def get_learning_record(video_id: int, db: Session = Depends(get_db)):
    """获取学习记录"""
    
    record = db.query(LearningRecord).filter(LearningRecord.video_id == video_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="学习记录不存在")
    
    return record

@router.put("/{video_id}", response_model=LearningRecordResponse)
async def update_learning_record(
    video_id: int,
    record_update: LearningRecordUpdate,
    db: Session = Depends(get_db)
):
    """更新学习记录"""
    
    record = db.query(LearningRecord).filter(LearningRecord.video_id == video_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="学习记录不存在")
    
    # 更新字段
    if record_update.learning_status is not None:
        # 状态变更逻辑
        if record_update.learning_status == "learning" and record.learning_status == "todo":
            record.started_at = datetime.utcnow()
        elif record_update.learning_status == "completed" and record.learning_status == "learning":
            record.completed_at = datetime.utcnow()
        
        record.learning_status = record_update.learning_status
    
    if record_update.practice_status is not None:
        record.practice_status = record_update.practice_status
    
    if record_update.notes is not None:
        record.notes = record_update.notes
    
    if record_update.code_repo is not None:
        record.code_repo = record_update.code_repo
    
    if record_update.priority is not None:
        record.priority = record_update.priority
    
    if record_update.estimated_time is not None:
        record.estimated_time = record_update.estimated_time
    
    if record_update.actual_time is not None:
        record.actual_time = record_update.actual_time
    
    record.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(record)
    
    return record

@router.get("/stats/overview", response_model=LearningStatsResponse)
async def get_learning_stats(db: Session = Depends(get_db)):
    """获取学习统计数据"""
    
    # 总视频数
    total_videos = db.query(Video).filter(Video.status == "completed").count()
    
    # 各状态统计
    completed_videos = db.query(LearningRecord).filter(LearningRecord.learning_status == "completed").count()
    learning_videos = db.query(LearningRecord).filter(LearningRecord.learning_status == "learning").count()
    todo_videos = db.query(LearningRecord).filter(LearningRecord.learning_status == "todo").count()
    
    # 已实践视频数
    practiced_videos = db.query(LearningRecord).filter(
        LearningRecord.practice_status.in_(["implementing", "completed"])
    ).count()
    
    # 总学习时长
    total_learning_time_result = db.query(func.sum(LearningRecord.actual_time)).filter(
        LearningRecord.actual_time.isnot(None)
    ).scalar()
    total_learning_time = total_learning_time_result or 0
    
    # 完成率
    completion_rate = (completed_videos / total_videos * 100) if total_videos > 0 else 0
    
    return LearningStatsResponse(
        total_videos=total_videos,
        completed_videos=completed_videos,
        learning_videos=learning_videos,
        todo_videos=todo_videos,
        total_learning_time=total_learning_time,
        practiced_videos=practiced_videos,
        completion_rate=round(completion_rate, 2)
    )