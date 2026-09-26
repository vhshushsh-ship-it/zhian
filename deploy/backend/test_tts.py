import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('DASHSCOPE_API_KEY')
base_url = os.getenv('DASHSCOPE_BASE_URL')

url = f'{base_url}/services/audio/tts/SpeechSynthesizer'
headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json'
}

body = {
    "model": os.getenv('DASHSCOPE_MODEL'),
    "input": {
        "text": "Hello, nice to meet you. How are you today?",
        "voice": "loongava_v3",
        "format": "mp3",
        "sample_rate": 24000,
        "rate": 1.0
    },
    "parameters": {
        "language_hints": ["en"]
    }
}

resp = requests.post(url, headers=headers, json=body, timeout=30)
print('HTTP 状态码:', resp.status_code)
result = resp.json()
print(json.dumps(result, ensure_ascii=False, indent=2))

if resp.status_code == 200 and result.get('output', {}).get('audio', {}).get('url'):
    audio_url = result['output']['audio']['url']
    audio_resp = requests.get(audio_url, timeout=30)
    with open('test_output.mp3', 'wb') as f:
        f.write(audio_resp.content)
    print('\n成功！音频大小:', len(audio_resp.content), '字节')
    print('双击 test_output.mp3 听发音')
