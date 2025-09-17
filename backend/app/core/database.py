from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime
from typing import Generator
from app.core.config import settings

# 数据库引擎
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}  # SQLite特有配置
)

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 基础模型类
Base = declarative_base()

# 数据库模型定义
class Video(Base):
    __tablename__ = "videos"
    
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(500), unique=True, nullable=False, index=True)
    title = Column(String(200))
    platform = Column(String(50), nullable=False, index=True)
    thumbnail_url = Column(String(500))
    duration = Column(Integer)  # 秒
    file_size = Column(Integer)  # 字节
    local_path = Column(String(300))
    file_fingerprint = Column(String(64), unique=True, index=True)  # SHA256哈希值
    status = Column(String(20), default="pending", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    transcript = relationship("Transcript", back_populates="video", uselist=False)
    learning_record = relationship("LearningRecord", back_populates="video", uselist=False)
    tasks = relationship("Task", back_populates="video")

class Transcript(Base):
    __tablename__ = "transcripts"
    
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False, index=True)
    original_text = Column(Text, nullable=False)
    cleaned_text = Column(Text)
    summary = Column(Text)
    tags = Column(String(200))
    language = Column(String(10), default="zh")
    confidence_score = Column(Float)
    processing_time = Column(Integer)  # 秒
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    video = relationship("Video", back_populates="transcript")

class LearningRecord(Base):
    __tablename__ = "learning_records"
    
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False, index=True)
    learning_status = Column(String(20), default="todo", index=True)  # todo, learning, completed
    practice_status = Column(String(20), default="none", index=True)  # none, planning, implementing, completed
    notes = Column(Text)
    code_repo = Column(String(200))
    priority = Column(Integer, default=3)  # 1-5
    estimated_time = Column(Integer)  # 分钟
    actual_time = Column(Integer)  # 分钟
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    video = relationship("Video", back_populates="learning_record")

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(50), unique=True, nullable=False, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), index=True)
    task_type = Column(String(30), nullable=False, index=True)  # download, extract, transcribe
    status = Column(String(20), default="pending", index=True)
    progress = Column(Integer, default=0)
    error_message = Column(Text)
    result = Column(Text)  # JSON格式
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    video = relationship("Video", back_populates="tasks")

class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    color = Column(String(7), default="#666666")
    created_at = Column(DateTime, default=datetime.utcnow)

# 数据库依赖
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 初始化数据库
async def init_db():
    Base.metadata.create_all(bind=engine)
    
    # 创建默认分类
    db = SessionLocal()
    try:
        default_categories = [
            {"name": "编程教程", "description": "编程相关的学习视频", "color": "#3B82F6"},
            {"name": "工具使用", "description": "软件工具使用教程", "color": "#10B981"},
            {"name": "框架学习", "description": "各种开发框架学习", "color": "#8B5CF6"},
            {"name": "待整理", "description": "暂未分类的视频", "color": "#6B7280"}
        ]
        
        for cat_data in default_categories:
            existing = db.query(Category).filter(Category.name == cat_data["name"]).first()
            if not existing:
                category = Category(**cat_data)
                db.add(category)
        
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"初始化分类失败: {e}")
    finally:
        db.close()