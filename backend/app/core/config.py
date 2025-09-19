from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "视频学习管理器"
    APP_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # 数据库配置
    DATABASE_URL: str = "sqlite:///./video_learning.db"
    
    # Redis配置
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # 文件存储配置
    UPLOAD_DIR: str = "/var/video-learning-manager/uploads"
    VIDEO_DIR: str = "/var/video-learning-manager/videos"
    AUDIO_DIR: str = "/var/video-learning-manager/audios"
    THUMBNAIL_DIR: str = "/var/video-learning-manager/thumbnails"
    
    # AI转录配置
    TRANSCRIPTION_MODE: str = "local"  # local, auto
    FORCE_CPU_MODE: bool = False  # 强制CPU模式（开发环境）
    AUTO_GPU_DETECTION: bool = True  # 自动检测GPU
    
    # 本地模型配置
    WHISPER_MODEL: str = "small"  # 开发用small，生产用base/large
    WHISPER_DEVICE: str = "auto"  # auto, cpu, cuda
    WHISPER_COMPUTE_TYPE: str = "auto"  # auto, int8, float16, float32
    WHISPER_NUM_WORKERS: int = 1  # 开发环境限制1个
    WHISPER_THREADS: int = 2
    
    # 环境检测配置
    ENVIRONMENT: str = "auto"  # auto, development, production
    DEV_CPU_LIMIT: float = 70.0  # 开发环境CPU限制
    PROD_CPU_LIMIT: float = 90.0  # 生产环境CPU限制
    
    # 安全配置
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # 任务队列配置
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # 视频处理配置
    MAX_VIDEO_SIZE: int = 500 * 1024 * 1024  # 500MB
    MAX_PROCESSING_TIME: int = 1800  # 30分钟
    SUPPORTED_PLATFORMS: list = ["douyin", "weixin", "bilibili", "youtube"]
    
    # 并发控制配置
    MAX_CONCURRENT_TRANSCRIPTIONS: int = 1  # 最大同时转录数量
    TRANSCRIPTION_QUEUE_SIZE: int = 10  # 转录队列大小
    
    # 本地视频监控配置
    LOCAL_VIDEO_DIR: str = "/Users/user/Documents/AI-MCP-Store/video-learning-manager/local-videos"
    ENABLE_LOCAL_SCAN: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# 创建配置实例
settings = Settings()

# 确保目录存在
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.VIDEO_DIR, exist_ok=True)
os.makedirs(settings.AUDIO_DIR, exist_ok=True)
os.makedirs(settings.THUMBNAIL_DIR, exist_ok=True)