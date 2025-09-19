"""
系统资源监控工具
监控CPU、GPU、内存使用情况
"""
import psutil
import logging
from typing import Dict, Optional
import subprocess
import json

logger = logging.getLogger(__name__)

class SystemMonitor:
    def __init__(self):
        self.gpu_available = self._check_gpu_availability()
    
    def _check_gpu_availability(self) -> bool:
        """检查GPU是否可用"""
        try:
            # 检查NVIDIA GPU
            result = subprocess.run(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                logger.info(f"🎮 检测到NVIDIA GPU: {result.stdout.strip()}")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        try:
            # 检查是否有CUDA支持
            import torch
            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_name(0)
                logger.info(f"🎮 检测到CUDA GPU: {gpu_name}")
                return True
        except ImportError:
            pass
        
        logger.info("💻 未检测到可用GPU，将使用CPU模式")
        return False
    
    def get_cpu_usage(self) -> float:
        """获取CPU使用率"""
        return psutil.cpu_percent(interval=1)
    
    def get_memory_usage(self) -> Dict[str, float]:
        """获取内存使用情况"""
        memory = psutil.virtual_memory()
        return {
            "total": memory.total / (1024**3),  # GB
            "used": memory.used / (1024**3),    # GB
            "available": memory.available / (1024**3),  # GB
            "percent": memory.percent
        }
    
    def get_gpu_usage(self) -> Optional[Dict]:
        """获取GPU使用情况"""
        if not self.gpu_available:
            return None
        
        try:
            # 使用nvidia-smi获取GPU信息
            cmd = [
                'nvidia-smi', 
                '--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu',
                '--format=csv,nounits,noheader'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                data = result.stdout.strip().split(',')
                if len(data) >= 4:
                    return {
                        "utilization": float(data[0].strip()),
                        "memory_used": float(data[1].strip()),
                        "memory_total": float(data[2].strip()),
                        "temperature": float(data[3].strip())
                    }
        except (subprocess.TimeoutExpired, ValueError, IndexError) as e:
            logger.warning(f"获取GPU信息失败: {e}")
        
        # 尝试使用PyTorch获取GPU信息
        try:
            import torch
            if torch.cuda.is_available():
                gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                gpu_allocated = torch.cuda.memory_allocated(0) / (1024**3)
                return {
                    "memory_total": gpu_memory,
                    "memory_used": gpu_allocated,
                    "memory_available": gpu_memory - gpu_allocated,
                    "utilization": "N/A"
                }
        except ImportError:
            pass
        
        return None
    
    def get_system_status(self) -> Dict:
        """获取完整的系统状态"""
        cpu_usage = self.get_cpu_usage()
        memory_info = self.get_memory_usage()
        gpu_info = self.get_gpu_usage()
        
        # 判断系统负载状态
        load_status = "low"
        if cpu_usage > 80:
            load_status = "high"
        elif cpu_usage > 50:
            load_status = "medium"
        
        return {
            "timestamp": psutil.boot_time(),
            "cpu": {
                "usage_percent": cpu_usage,
                "load_avg": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None,
                "cores": psutil.cpu_count()
            },
            "memory": memory_info,
            "gpu": gpu_info,
            "load_status": load_status,
            "gpu_available": self.gpu_available
        }
    
    def is_suitable_for_transcription(self) -> tuple[bool, str]:
        """判断当前系统状态是否适合进行转录任务"""
        status = self.get_system_status()
        
        cpu_usage = status["cpu"]["usage_percent"]
        memory_percent = status["memory"]["percent"]
        
        # 开发环境的负载检查（更严格）
        if not self.gpu_available:
            if cpu_usage > 70:
                return False, f"CPU负载过高 ({cpu_usage:.1f}%)，建议等待"
            if memory_percent > 85:
                return False, f"内存不足 ({memory_percent:.1f}%)，建议等待"
            return True, f"系统负载正常 (CPU: {cpu_usage:.1f}%, 内存: {memory_percent:.1f}%)"
        
        # 生产环境的负载检查（相对宽松）
        else:
            if cpu_usage > 90:
                return False, f"CPU负载极高 ({cpu_usage:.1f}%)，建议等待"
            if memory_percent > 95:
                return False, f"内存严重不足 ({memory_percent:.1f}%)，建议等待"
            return True, f"GPU环境负载正常 (CPU: {cpu_usage:.1f}%, 内存: {memory_percent:.1f}%)"
    
    def log_system_status(self):
        """记录系统状态到日志"""
        status = self.get_system_status()
        
        logger.info("📊 === 系统状态监控 ===")
        logger.info(f"💻 CPU使用率: {status['cpu']['usage_percent']:.1f}%")
        logger.info(f"🧠 内存使用: {status['memory']['percent']:.1f}% ({status['memory']['used']:.1f}GB / {status['memory']['total']:.1f}GB)")
        
        if status['gpu']:
            gpu = status['gpu']
            logger.info(f"🎮 GPU使用率: {gpu.get('utilization', 'N/A')}%")
            logger.info(f"🎮 GPU内存: {gpu.get('memory_used', 0):.1f}GB / {gpu.get('memory_total', 0):.1f}GB")
            if 'temperature' in gpu:
                logger.info(f"🌡️ GPU温度: {gpu['temperature']}°C")
        else:
            logger.info("🎮 GPU: 未检测到可用GPU")
        
        logger.info(f"📈 系统负载状态: {status['load_status']}")

# 全局监控实例
system_monitor = SystemMonitor()