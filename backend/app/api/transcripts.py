from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db, Transcript
from app.models.schemas import TranscriptResponse, TranscriptUpdate

router = APIRouter()

@router.get("/{video_id}", response_model=TranscriptResponse)
async def get_transcript(video_id: int, db: Session = Depends(get_db)):
    """获取视频字幕"""
    
    transcript = db.query(Transcript).filter(Transcript.video_id == video_id).first()
    if not transcript:
        raise HTTPException(status_code=404, detail="字幕不存在")
    
    return transcript

@router.put("/{video_id}", response_model=TranscriptResponse)
async def update_transcript(
    video_id: int,
    transcript_update: TranscriptUpdate,
    db: Session = Depends(get_db)
):
    """更新字幕内容"""
    
    transcript = db.query(Transcript).filter(Transcript.video_id == video_id).first()
    if not transcript:
        raise HTTPException(status_code=404, detail="字幕不存在")
    
    # 更新字段
    if transcript_update.cleaned_text is not None:
        transcript.cleaned_text = transcript_update.cleaned_text
    
    if transcript_update.summary is not None:
        transcript.summary = transcript_update.summary
    
    if transcript_update.tags is not None:
        transcript.tags = transcript_update.tags
    
    db.commit()
    db.refresh(transcript)
    
    return transcript