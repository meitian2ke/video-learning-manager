"""
系统状态API接口
提供CPU、GPU、内存使用情况和转录模式信息
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from app.utils.system_monitor import system_monitor
from app.services.ai_service import ai_service
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/system/status")
async def get_system_status() -> Dict[str, Any]:
    """获取系统状态"""
    try:
        # 获取系统监控信息
        status = system_monitor.get_system_status()
        can_transcribe, load_msg = system_monitor.is_suitable_for_transcription()
        
        # 获取AI服务信息
        current_mode = getattr(ai_service, 'current_mode', None)
        environment = getattr(ai_service, 'environment', 'unknown')
        
        return {
            "timestamp": status["timestamp"],
            "system": {
                "cpu": status["cpu"],
                "memory": status["memory"],
                "gpu": status["gpu"],
                "load_status": status["load_status"],
                "can_transcribe": can_transcribe,
                "load_message": load_msg
            },
            "transcription": {
                "current_mode": "local",
                "configured_mode": settings.TRANSCRIPTION_MODE,
                "environment": environment,
                "gpu_available": status["gpu_available"],
                "force_cpu": settings.FORCE_CPU_MODE,
                "model": settings.WHISPER_MODEL,
                "device": "GPU" if status["gpu_available"] and not settings.FORCE_CPU_MODE else "CPU"
            },
            "configuration": {
                "max_concurrent": settings.MAX_CONCURRENT_TRANSCRIPTIONS,
                "available_slots": getattr(ai_service, 'transcription_semaphore', {}).get('_value', 'N/A'),
                "dev_cpu_limit": settings.DEV_CPU_LIMIT,
                "prod_cpu_limit": settings.PROD_CPU_LIMIT
            }
        }
    except Exception as e:
        logger.error(f"获取系统状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取系统状态失败: {str(e)}")

@router.post("/system/transcription-mode")
async def set_transcription_mode(mode: str) -> Dict[str, str]:
    """手动设置转录模式（仅支持本地模式）"""
    try:
        valid_modes = ["local", "auto"]
        if mode not in valid_modes:
            raise HTTPException(
                status_code=400, 
                detail=f"无效的转录模式: {mode}. 有效选项: {valid_modes}"
            )
        
        # 更新配置（注意：这只是临时更新，重启后会恢复）
        settings.TRANSCRIPTION_MODE = mode
        
        logger.info(f"📝 转录模式已更新为: {mode}")
        
        return {
            "message": f"转录模式已设置为: {mode}",
            "previous_mode": getattr(ai_service, 'current_mode', 'local'),
            "new_mode": mode,
            "note": "仅支持本地转录模式"
        }
    except Exception as e:
        logger.error(f"设置转录模式失败: {e}")
        raise HTTPException(status_code=500, detail=f"设置转录模式失败: {str(e)}")

@router.post("/system/force-cpu")
async def toggle_force_cpu(force: bool) -> Dict[str, Any]:
    """切换强制CPU模式"""
    try:
        settings.FORCE_CPU_MODE = force
        
        # 如果有已加载的模型，需要重新加载以应用新设置
        if hasattr(ai_service, 'model') and ai_service.model is not None:
            logger.info("🔄 检测到设备模式变更，将在下次转录时重新加载模型")
            ai_service.model = None  # 重置模型，下次使用时会重新加载
        
        logger.info(f"🔧 强制CPU模式已{'启用' if force else '禁用'}")
        
        return {
            "message": f"强制CPU模式已{'启用' if force else '禁用'}",
            "force_cpu": force,
            "will_reload_model": True
        }
    except Exception as e:
        logger.error(f"切换强制CPU模式失败: {e}")
        raise HTTPException(status_code=500, detail=f"切换强制CPU模式失败: {str(e)}")

@router.get("/system/performance-tips")
async def get_performance_tips() -> Dict[str, Any]:
    """获取性能优化建议"""
    try:
        status = system_monitor.get_system_status()
        tips = []
        
        cpu_usage = status["cpu"]["usage_percent"]
        memory_percent = status["memory"]["percent"]
        gpu_available = status["gpu_available"]
        environment = getattr(ai_service, 'environment', 'unknown')
        
        # CPU负载建议
        if cpu_usage > 80:
            tips.append({
                "type": "warning",
                "title": "CPU负载过高",
                "message": f"当前CPU使用率 {cpu_usage:.1f}%，建议暂停其他高负载任务",
                "action": "考虑切换到云端转录或降低并发数"
            })
        elif cpu_usage > 60:
            tips.append({
                "type": "info",
                "title": "CPU负载较高",
                "message": f"当前CPU使用率 {cpu_usage:.1f}%，监控系统性能",
                "action": "如果转录缓慢可考虑云端转录"
            })
        
        # 内存建议
        if memory_percent > 85:
            tips.append({
                "type": "warning",
                "title": "内存不足",
                "message": f"内存使用率 {memory_percent:.1f}%，可能影响转录性能",
                "action": "关闭不必要的应用程序或使用云端转录"
            })
        
        # GPU建议
        if not gpu_available:
            tips.append({
                "type": "info",
                "title": "GPU未检测到",
                "message": "当前使用CPU模式，转录速度较慢",
                "action": "如有GPU可考虑安装CUDA支持以获得更好性能"
            })
        elif gpu_available:
            tips.append({
                "type": "success",
                "title": "GPU已启用",
                "message": "检测到GPU，转录性能将大幅提升",
                "action": "建议使用更大的模型(base/large)以获得更好准确度"
            })
        
        # 环境建议
        if environment == "development":
            tips.append({
                "type": "success",
                "title": "开发环境优化",
                "message": "已启用开发环境优化设置",
                "action": "单任务模式，CPU负载限制70%"
            })
        elif environment == "production":
            tips.append({
                "type": "success",
                "title": "生产环境模式",
                "message": "已检测到GPU，启用生产环境模式",
                "action": "可使用多任务并发和GPU加速"
            })
        
        return {
            "environment": environment,
            "system_status": {
                "cpu_usage": cpu_usage,
                "memory_usage": memory_percent,
                "gpu_available": gpu_available
            },
            "tips": tips,
            "recommendations": {
                "best_mode": "local",
                "max_concurrent": 1 if environment == "development" else (3 if gpu_available else 1),
                "model_suggestion": "small" if not gpu_available else "base",
                "device_recommendation": "GPU" if gpu_available else "CPU"
            }
        }
    except Exception as e:
        logger.error(f"获取性能建议失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取性能建议失败: {str(e)}")