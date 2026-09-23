import api from './client'

/**
 * 上传录音音频，调用后端阿里云百炼 ASR 转成英文文字。
 * 返回识别出的文字（无有效内容时为空串）。
 */
export async function recognizeAudio(blob: Blob): Promise<{ text: string }> {
  const formData = new FormData()
  const file = new File([blob], 'recording.webm', {
    type: blob.type || 'audio/webm',
  })
  formData.append('file', file)
  const res = await api.post<{ text: string }>('/speaking/asr', formData)
  return res.data
}
