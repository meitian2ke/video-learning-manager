from fastapi import APIRouter
import subprocess
import psutil
import json
from typing import Dict, Any

router = APIRouter()

@router.get("/monitor/lite")
async def get_system_monitor_lite():
    """轻量级系统监控数据 - 用于页面顶部显示"""
    
    try:
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # 内存使用率
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used = round(memory.used / 1024 / 1024 / 1024, 1)  # GB
        memory_total = round(memory.total / 1024 / 1024 / 1024, 1)  # GB
        
        # GPU状态
        gpu_status = await get_gpu_status_lite()
        
        # 获取转录队列状态（从环境变量或配置）
        import os
        max_concurrent = int(os.getenv('MAX_CONCURRENT_TRANSCRIPTIONS', 3))
        
        # 检查是否有转录进程在运行
        transcription_active = False
        try:
            # 检查是否有Python进程在使用GPU
            result = subprocess.run(
                ["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=2
            )
            transcription_active = bool(result.stdout.strip())
        except:
            pass
        
        return {
            "cpu": {
                "usage": round(cpu_percent, 1),
                "status": "high" if cpu_percent > 80 else "normal" if cpu_percent > 50 else "low"
            },
            "memory": {
                "usage": memory_percent,
                "used": memory_used,
                "total": memory_total,
                "status": "high" if memory_percent > 80 else "normal" if memory_percent > 60 else "low"
            },
            "gpu": gpu_status,
            "transcription": {
                "active": transcription_active,
                "max_concurrent": max_concurrent,
                "mode": "GPU" if gpu_status.get("available") else "CPU"
            },
            "timestamp": psutil.boot_time()
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "cpu": {"usage": 0, "status": "unknown"},
            "memory": {"usage": 0, "used": 0, "total": 0, "status": "unknown"},
            "gpu": {"available": False, "usage": 0, "memory": 0, "status": "unknown"},
            "transcription": {"active": False, "max_concurrent": 3, "mode": "CPU"}
        }


async def get_gpu_status_lite() -> Dict[str, Any]:
    """获取GPU状态 - 轻量级版本"""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu", 
             "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=2
        )
        
        if result.returncode == 0:
            gpu_data = result.stdout.strip().split(', ')
            utilization = int(gpu_data[0])
            memory_used = int(gpu_data[1])
            memory_total = int(gpu_data[2])
            temperature = int(gpu_data[3])
            
            return {
                "available": True,
                "usage": utilization,
                "memory": round((memory_used / memory_total) * 100, 1),
                "memory_used": memory_used,
                "memory_total": memory_total,
                "temperature": temperature,
                "status": "high" if utilization > 80 else "normal" if utilization > 30 else "low"
            }
        else:
            return {"available": False, "usage": 0, "memory": 0, "status": "unavailable"}
            
    except Exception:
        return {"available": False, "usage": 0, "memory": 0, "status": "error"}


@router.get("/monitor/queue")
async def get_transcription_queue():
    """获取转录队列状态"""
    try:
        # 这里可以扩展为实际的队列监控
        # 目前返回基本状态
        return {
            "pending": 0,  # 待处理数量
            "processing": 0,  # 正在处理数量
            "completed": 0,  # 已完成数量
            "failed": 0  # 失败数量
        }
    except Exception as e:
        return {"error": str(e)}