"""
Celery应用配置
处理视频转录的分布式任务队列
"""

from celery import Celery
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# 创建Celery应用实例
celery_app = Celery(
    "video_processing",
    broker=settings.REDIS_URL,  # Redis作为消息队列
    backend=settings.REDIS_URL,  # Redis存储任务结果
    include=['app.tasks.video_tasks']  # 包含任务模块
)

# Celery配置
celery_app.conf.update(
    # 序列化配置
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # 时区配置
    timezone='Asia/Shanghai',
    enable_utc=True,
    
    # Worker配置
    worker_prefetch_multiplier=1,  # 每个worker一次只预取一个任务，避免GPU资源争抢
    task_acks_late=True,  # 任务完成后才确认，保证不丢失任务
    worker_max_tasks_per_child=10,  # 每个worker最多处理10个任务后重启，防止内存泄漏
    
    # 任务配置
    task_soft_time_limit=3600,  # 软超时1小时
    task_time_limit=3900,  # 硬超时65分钟
    task_max_retries=3,  # 最大重试3次
    task_default_retry_delay=300,  # 默认重试延迟5分钟
    
    # 结果配置
    result_expires=86400,  # 任务结果保存1天
    
    # 路由配置
    task_routes={
        'app.tasks.video_tasks.process_video_task': {'queue': 'video_processing'},
        'app.tasks.video_tasks.batch_process_videos': {'queue': 'video_processing'},
    },
    
    # 队列配置
    task_default_queue='video_processing',
    task_queues={
        'video_processing': {
            'exchange': 'video_processing',
            'routing_key': 'video_processing',
        }
    }
)

# Celery信号处理
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """设置定期任务"""
    # 每30分钟清理GPU内存
    sender.add_periodic_task(
        1800.0,  # 30分钟
        cleanup_gpu_memory.s(),
        name='cleanup GPU memory every 30 minutes'
    )

@celery_app.task
def cleanup_gpu_memory():
    """定期清理GPU内存"""
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
            logger.info("🧹 GPU内存清理完成")
        return "GPU memory cleaned"
    except Exception as e:
        logger.error(f"❌ GPU内存清理失败: {e}")
        return f"GPU memory cleanup failed: {e}"