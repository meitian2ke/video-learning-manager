from pydantic import BaseModel, HttpUrl, Field, AnyUrl
from typing import Optional, List
from datetime import datetime
from enum import Enum

# 枚举类型
class VideoStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class LearningStatus(str, Enum):
    TODO = "todo"
    LEARNING = "learning"
    COMPLETED = "completed"

class PracticeStatus(str, Enum):
    NONE = "none"
    PLANNING = "planning"
    IMPLEMENTING = "implementing"
    COMPLETED = "completed"

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

# 基础模型
class VideoBase(BaseModel):
    url: AnyUrl
    title: Optional[str] = None
    platform: str

class VideoCreate(VideoBase):
    category_ids: Optional[List[int]] = []

class VideoUpdate(BaseModel):
    title: Optional[str] = None
    category_ids: Optional[List[int]] = None

class VideoResponse(VideoBase):
    id: int
    status: VideoStatus
    thumbnail_url: Optional[str] = None
    duration: Optional[int] = None
    file_size: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# 字幕模型
class TranscriptBase(BaseModel):
    original_text: str
    cleaned_text: Optional[str] = None
    summary: Optional[str] = None
    tags: Optional[str] = None
    language: str = "zh"
    confidence_score: Optional[float] = None

class TranscriptCreate(TranscriptBase):
    video_id: int

class TranscriptUpdate(BaseModel):
    cleaned_text: Optional[str] = None
    summary: Optional[str] = None
    tags: Optional[str] = None

class TranscriptResponse(TranscriptBase):
    id: int
    video_id: int
    processing_time: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# 学习记录模型
class LearningRecordBase(BaseModel):
    learning_status: LearningStatus = LearningStatus.TODO
    practice_status: PracticeStatus = PracticeStatus.NONE
    notes: Optional[str] = None
    code_repo: Optional[str] = None
    priority: int = Field(default=3, ge=1, le=5)
    estimated_time: Optional[int] = None

class LearningRecordCreate(LearningRecordBase):
    video_id: int

class LearningRecordUpdate(BaseModel):
    learning_status: Optional[LearningStatus] = None
    practice_status: Optional[PracticeStatus] = None
    notes: Optional[str] = None
    code_repo: Optional[str] = None
    priority: Optional[int] = Field(default=None, ge=1, le=5)
    estimated_time: Optional[int] = None
    actual_time: Optional[int] = None

class LearningRecordResponse(LearningRecordBase):
    id: int
    video_id: int
    actual_time: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# 任务模型
class TaskResponse(BaseModel):
    id: int
    task_id: str
    video_id: Optional[int] = None
    task_type: str
    status: TaskStatus
    progress: int
    error_message: Optional[str] = None
    result: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# 分类模型
class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    color: str = "#666666"

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# 复合响应模型
class VideoDetailResponse(VideoResponse):
    transcript: Optional[TranscriptResponse] = None
    learning_record: Optional[LearningRecordResponse] = None
    categories: List[CategoryResponse] = []

class VideoListResponse(BaseModel):
    items: List[VideoDetailResponse]
    total: int
    page: int
    size: int
    pages: int

# 请求模型
class VideoProcessRequest(BaseModel):
    url: AnyUrl
    category_ids: Optional[List[int]] = []
    priority: Optional[int] = Field(default=3, ge=1, le=5)

class LearningStatsResponse(BaseModel):
    total_videos: int
    pending_videos: int
    processing_videos: int
    completed_videos: int
    learning_videos: int
    todo_videos: int
    total_learning_time: int  # 分钟
    practiced_videos: int
    completion_rate: float