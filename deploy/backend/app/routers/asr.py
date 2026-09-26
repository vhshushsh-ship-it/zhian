"""英语口语：阿里云百炼（DashScope）语音识别（ASR）。

前端录下用户英语语音上传到本接口，本接口用 httpx 直连百炼
fun-asr-flash 同步识别接口，把语音转成文字返回，供口语练习页填入输入框。

浏览器默认录成 webm/opus，后端先用 pydub + ffmpeg 转成 WAV，再转成 base64
data URI 作为输入音频。fun-asr-flash 是同步接口，直接返回识别文本，无需轮询。

调用方式参考 tts.py：纯 HTTP 直连，不依赖 dashscope SDK，端点用
settings.dashscope_base_url 拼路径（与 TTS 同一个百炼工作空间域名）。
"""

import base64
import json
import logging
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from ..config import settings
from ..deps import get_current_user
from ..models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/speaking", tags=["asr"])

# 语音识别模型（用户已开通的 fun-asr-flash 版本）
ASR_MODEL = "fun-asr-flash-2026-06-15"

# 请求超时（秒）
REQUEST_TIMEOUT = 60.0

# 上传音频大小上限（约 10MB）
MAX_AUDIO_BYTES = 10 * 1024 * 1024

# 可识别的音频格式（用于从 content_type / 后缀推断）
SUPPORTED_FORMATS = ("webm", "wav", "mp3", "ogg", "m4a", "flac", "aac", "opus")

# 音频格式 → base64 data URL 的 MIME 类型
_FORMAT_MIME = {
    "wav": "audio/wav",
    "mp3": "audio/mpeg",
    "m4a": "audio/mp4",
    "flac": "audio/flac",
    "ogg": "audio/ogg",
    "opus": "audio/ogg",
    "aac": "audio/aac",
    "webm": "audio/webm",
}


def _detect_format(content_type: str | None, filename: str | None) -> str:
    """根据上传文件的 content_type / 文件名推断音频格式。"""
    ct = (content_type or "").lower()
    for fmt in SUPPORTED_FORMATS:
        if fmt in ct:
            return fmt
    ext = Path(filename or "").suffix.lower().lstrip(".")
    if ext in SUPPORTED_FORMATS:
        return ext
    # 浏览器 MediaRecorder 默认 webm，兜底用它
    return "webm"


def _convert_to_wav(audio: bytes) -> bytes | None:
    """尽力把音频统一转成 WAV（16-bit PCM）。

    浏览器默认录的 webm/opus 识别服务不支持，这里用 pydub + ffmpeg 转成 WAV。
    转换失败（未装 pydub / 无 ffmpeg / 解码失败）返回 None，由调用方决定是否
    按原格式透传。
    """
    try:
        from io import BytesIO

        from pydub import AudioSegment

        seg = AudioSegment.from_file(BytesIO(audio))
        out = BytesIO()
        seg.export(out, format="wav")
        return out.getvalue()
    except Exception as exc:  # noqa: BLE001 - 尽力而为，失败回退透传
        logger.warning("音频转 WAV 失败，将按原格式透传: %s", exc)
        return None


def _parse_result(resp: httpx.Response) -> dict:
    """解析响应体：兼容纯 JSON 与 X-DashScope-SSE 的 `data:` 事件流。"""
    body = resp.text
    if "data:" in body:
        for raw in body.splitlines():
            line = raw.strip()
            if not line.startswith("data:"):
                continue
            payload = line[len("data:"):].strip()
            if not payload or payload == "[DONE]":
                continue
            try:
                return json.loads(payload)
            except ValueError:
                continue
    return resp.json()


def _extract_text(result: dict) -> str:
    """从 fun-asr-flash 返回的 JSON 中提取识别文本。

    兼容多种返回结构，依次尝试：
      1. 顶层 text 字段（fun-asr-flash 实际返回在这里）
      2. output.text
      3. output.choices[0].message.content
    """
    # 1) 顶层 text（fun-asr-flash 实际返回位置）
    text = result.get("text")
    if isinstance(text, str) and text.strip():
        return text.strip()

    output = result.get("output")
    if isinstance(output, dict):
        # 2) output.text
        text = output.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()

        # 3) output.choices[0].message.content
        choices = output.get("choices")
        if isinstance(choices, list) and choices:
            message = choices[0].get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str) and content.strip():
                    return content.strip()

    return ""


@router.post("/asr")
async def recognize(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """上传音频 → 百炼语音识别 → 返回文字（需登录）。"""
    if not settings.dashscope_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="语音服务暂时不可用",
        )

    audio = await file.read()
    if not audio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="音频文件为空"
        )
    if len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="音频文件过大"
        )

    fmt = _detect_format(file.content_type, file.filename)

    # 浏览器默认 webm/opus，识别服务不支持，先统一转成 WAV
    if fmt != "wav":
        wav = _convert_to_wav(audio)
        if wav is not None:
            audio = wav
            fmt = "wav"

    # 转成 base64 data URI，作为输入音频
    mime = _FORMAT_MIME.get(fmt, "audio/wav")
    data_uri = f"data:{mime};base64,{base64.b64encode(audio).decode('ascii')}"

    url = (
        f"{settings.dashscope_base_url.rstrip('/')}"
        "/services/aigc/multimodal-generation/generation"
    )
    headers = {
        "Authorization": f"Bearer {settings.dashscope_api_key}",
        "Content-Type": "application/json",
        "X-DashScope-SSE": "enable",
    }
    payload = {
        "model": ASR_MODEL,
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {"data": data_uri},
                        }
                    ],
                }
            ]
        },
        "parameters": {"format": fmt},
    }

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        try:
            resp = await client.post(url, headers=headers, json=payload)
        except httpx.HTTPError as exc:
            logger.error("百炼 ASR 请求失败: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="语音识别失败",
            )

        if resp.status_code != 200:
            logger.error("百炼 ASR 返回非 200：%s %s", resp.status_code, resp.text)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="语音识别失败",
            )

        try:
            result = _parse_result(resp)
        except ValueError:
            logger.error("百炼 ASR 返回非 JSON：%s", resp.text)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="语音识别失败",
            )

        text = _extract_text(result)
        if not text:
            logger.warning("百炼 ASR 未返回识别文本：%s", result)

    return {"text": text}
