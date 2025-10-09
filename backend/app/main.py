from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import logging
import sys
from pathlib import Path
from app.core.database import init_db
from app.api import videos, transcripts, learning, local_videos, system, system_status, gpu_monitor, system_monitor

# 配置详细日志
def setup_logging():
    # 确保日志目录存在
    log_dir = Path("/app/logs")
    log_dir.mkdir(exist_ok=True)
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    
    # 文件处理器 - 详细日志
    file_handler = logging.FileHandler('/app/logs/video_processing.log', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # 控制台处理器 - 基本日志
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # 配置FastAPI相关日志
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("app").setLevel(logging.DEBUG)
    
    logging.info("=== 视频学习管理器启动 ===")

setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化数据库
    await init_db()
    
    # 自动启动本地视频监控
    from app.services.local_video_scanner import get_scanner
    from app.core.config import settings
    
    if settings.ENABLE_LOCAL_SCAN:
        try:
            scanner = get_scanner(settings.LOCAL_VIDEO_DIR)
            if scanner:
                scanner.start_watching()
                print(f"✅ 本地视频监控已启动: {settings.LOCAL_VIDEO_DIR}")
            else:
                print("⚠️ 本地视频监控启动失败")
        except Exception as e:
            print(f"❌ 启动本地视频监控失败: {e}")
    
    yield
    
    # 关闭时清理资源
    try:
        scanner = get_scanner()
        if scanner:
            scanner.stop_watching()
            print("🛑 本地视频监控已停止")
    except Exception as e:
        print(f"停止监控时出错: {e}")

app = FastAPI(
    title="视频学习管理器",
    description="智能视频字幕提取和学习管理系统",
    version="1.0.0",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(videos.router, prefix="/api/videos", tags=["videos"])
app.include_router(transcripts.router, prefix="/api/transcripts", tags=["transcripts"])
app.include_router(learning.router, prefix="/api/learning", tags=["learning"])
app.include_router(local_videos.router, prefix="/api/local-videos", tags=["local-videos"])
app.include_router(system.router, prefix="/api/system", tags=["system"])
app.include_router(system_status.router, prefix="/api", tags=["system-status"])
app.include_router(gpu_monitor.router, prefix="/api", tags=["gpu-monitor"])
app.include_router(system_monitor.router, prefix="/api", tags=["system-monitor"])

@app.get("/")
async def root():
    return {"message": "视频学习管理器 API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)