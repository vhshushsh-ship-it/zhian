"""英语口语：阿里云百炼（DashScope）语音合成（TTS）。

用 httpx 直接调用百炼新版 SpeechSynthesizer HTTP 接口：
- 先 POST 请求合成接口，拿到音频 URL；
- 再用 GET 下载音频二进制，返回给前端 <audio> 播放。

不依赖 dashscope SDK 的 SpeechSynthesizer.call（该 SDK 调用方式与新版
API 不匹配），改用纯 HTTP 调用，模型 / 发音人 / 语速等参数集中在上方常量。
"""

import logging
import time

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from ..config import settings
from ..deps import get_current_user_from_query
from ..models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tts", tags=["tts"])

# 发音人：loongbetty_v3（美式英文音色，效果不理想可在此替换）
TTS_VOICE = "loongbetty_v3"
# 采样率
TTS_SAMPLE_RATE = 24000
# 音频格式
TTS_FORMAT = "mp3"

# 内存缓存有效期（秒）：同一句话 10 分钟内不重复调用 API
CACHE_TTL = 600
# 简单内存缓存：cache_key(text|rate) -> (时间戳, 音频字节)
_cache: dict[str, tuple[float, bytes]] = {}

# 请求超时（秒）
REQUEST_TIMEOUT = 30.0


@router.get("/speak")
async def speak(
    text: str = Query(..., description="要合成的英文文本"),
    rate: float = Query(1.0, ge=0.5, le=2.0, description="语速"),
    current_user: User = Depends(get_current_user_from_query),
):
    """合成英文语音并直接返回 MP3 音频流（需登录，token 走 query 参数）。

    <audio> 标签无法携带 Authorization 请求头，因此这里用
    get_current_user_from_query 从 query 的 token 参数完成鉴权。
    """
    if not text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="text 不能为空")

    # 限制文本长度，避免过长的合成请求
    if len(text) > 500:
        text = text[:500]

    cache_key = f"{text}|{rate}"
    now = time.time()

    # 清理过期缓存
    for key in [k for k, (t, _) in _cache.items() if now - t > CACHE_TTL]:
        _cache.pop(key, None)

    # 命中缓存直接返回
    if cache_key in _cache:
        _, audio = _cache[cache_key]
        return Response(content=audio, media_type="audio/mpeg")

    if not settings.dashscope_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="语音服务暂时不可用",
        )

    # POST 调用百炼语音合成接口，拿到音频 URL
    url = f"{settings.dashscope_base_url.rstrip('/')}/services/audio/tts/SpeechSynthesizer"
    headers = {
        "Authorization": f"Bearer {settings.dashscope_api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": settings.dashscope_model,
        "input": {
            "text": text,
            "voice": TTS_VOICE,
            "format": TTS_FORMAT,
            "sample_rate": TTS_SAMPLE_RATE,
            "rate": rate,
        },
        "parameters": {"language_hints": ["en"]},
    }

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        try:
            resp = await client.post(url, headers=headers, json=body)
        except httpx.HTTPError as exc:
            logger.error("百炼 TTS 合成请求失败: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="语音合成失败",
            )

        if resp.status_code != 200:
            logger.error("百炼 TTS 返回非 200：%s %s", resp.status_code, resp.text)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="语音合成失败",
            )

        result = resp.json()
        audio_url = result.get("output", {}).get("audio", {}).get("url")
        if not audio_url:
            logger.error("百炼 TTS 未返回音频 URL：%s", result)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="未获取到音频 URL",
            )

        # GET 下载音频二进制
        try:
            audio_resp = await client.get(audio_url)
        except httpx.HTTPError as exc:
            logger.error("下载音频失败: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="音频下载失败",
            )

        if audio_resp.status_code != 200:
            logger.error("下载音频返回非 200：%s", audio_resp.status_code)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="音频下载失败",
            )

        audio_data = audio_resp.content

    _cache[cache_key] = (now, audio_data)
    return Response(content=audio_data, media_type="audio/mpeg")
