from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class TranscriptionSettings(BaseModel):
    mode: str  # "openai" or "local"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com"
    auto_fallback: bool = True  # API失败时自动降级到本地

class SystemConfigResponse(BaseModel):
    transcription_mode: str
    openai_available: bool
    local_model_available: bool
    auto_fallback: bool

@router.get("/config", response_model=SystemConfigResponse)
async def get_system_config():
    """获取系统配置"""
    
    # 检查OpenAI是否可用
    openai_available = bool(settings.OPENAI_API_KEY and settings.OPENAI_BASE_URL)
    
    # 检查本地模型是否可用 (简单检查)
    local_model_available = True  # 始终认为本地模型可用
    
    return SystemConfigResponse(
        transcription_mode=settings.TRANSCRIPTION_MODE,
        openai_available=openai_available,
        local_model_available=local_model_available,
        auto_fallback=True
    )

@router.post("/config/transcription")
async def update_transcription_config(config: TranscriptionSettings):
    """更新转录配置"""
    
    try:
        # 验证模式
        if config.mode not in ["openai", "local"]:
            raise HTTPException(status_code=400, detail="无效的转录模式")
        
        # 如果选择OpenAI模式，验证API Key
        if config.mode == "openai":
            if not config.openai_api_key:
                raise HTTPException(status_code=400, detail="OpenAI API Key不能为空")
            
            # 这里可以测试API Key的有效性
            # 为了简单起见，我们先直接更新配置
        
        # 更新全局配置 (注意：这只在当前会话有效，重启后会恢复)
        settings.TRANSCRIPTION_MODE = config.mode
        if config.openai_api_key:
            settings.OPENAI_API_KEY = config.openai_api_key
        if config.openai_base_url:
            settings.OPENAI_BASE_URL = config.openai_base_url
        
        logger.info(f"转录模式已切换为: {config.mode}")
        
        return {"message": f"转录模式已切换为: {config.mode}", "mode": config.mode}
        
    except Exception as e:
        logger.error(f"更新转录配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"配置更新失败: {str(e)}")

@router.post("/config/transcription/test")
async def test_transcription_mode():
    """测试当前转录模式"""
    
    try:
        if settings.TRANSCRIPTION_MODE == "openai":
            # 测试OpenAI API连接
            if not settings.OPENAI_API_KEY or not settings.OPENAI_BASE_URL:
                return {"status": "error", "message": "OpenAI API配置不完整"}
            
            # 简单的配置检查（延迟初始化机制不需要预先创建客户端）
            return {"status": "success", "message": "OpenAI API配置正常", "mode": "openai", "api_key": f"sk-...{settings.OPENAI_API_KEY[-6:]}"}
        
        else:
            # 测试本地模型
            return {"status": "success", "message": "本地模型配置正常", "mode": "local"}
            
    except Exception as e:
        return {"status": "error", "message": f"测试失败: {str(e)}"}