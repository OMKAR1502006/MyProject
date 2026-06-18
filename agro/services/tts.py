import os
import base64
import requests
from typing import Optional
from django.conf import settings

def _gemini_key() -> Optional[str]:
    k = os.getenv('GEMINI_API_KEY') or getattr(settings, 'GEMINI_API_KEY', None)
    if not k or k.strip() == '' or k.startswith('YOUR_'):
        return None
    return k.strip()

def _openai_key() -> Optional[str]:
    k = os.getenv('OPENAI_API_KEY') or getattr(settings, 'OPENAI_API_KEY', None)
    if not k or k.strip() == '' or k.startswith('YOUR_'):
        return None
    return k.strip()

def _language_name(code: str) -> str:
    lang = (code or 'en').split('-')[0].lower()
    mapping = {
        'kn': 'Kannada',
        'hi': 'Hindi',
        'mr': 'Marathi',
        'te': 'Telugu',
        'en': 'English'
    }
    return mapping.get(lang, 'English')

def generate_tts(text: str, language_code: str) -> Optional[bytes]:
    """
    Generates audio bytes for the given text.
    Priority:
    1. Gemini 2.0 Flash Audio Modality
    2. OpenAI TTS API
    3. Returns None (indicates browser client-side SpeechSynthesis fallback)
    """
    text = (text or "").strip()
    if not text:
        return None

    # Clean text to avoid markdown or extra markers in voice
    cleaned_text = text.replace('**', '').replace('*', '').replace('—', '-').strip()
    # Remove final AI signatures if any
    if "—" in cleaned_text:
         cleaned_text = cleaned_text.split("—")[0].strip()

    lang_name = _language_name(language_code)
    
    # 1. Gemini TTS (Generative Audio)
    g_key = _gemini_key()
    if g_key:
        try:
            headers = {
                'x-goog-api-key': g_key,
                'Content-Type': 'application/json'
            }
            url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
            payload = {
                "contents": [{
                    "parts": [{
                        "text": f"Please read the following text aloud in {lang_name}. Speak ONLY the text itself, without adding any introductory or concluding comments. Text: {cleaned_text}"
                    }]
                }],
                "generationConfig": {
                    "responseModalities": ["AUDIO"]
                }
            }
            # Use request timeout to fail fast
            r = requests.post(url, headers=headers, json=payload, timeout=10)
            if r.status_code == 200:
                data = r.json()
                candidates = data.get('candidates', [])
                if candidates:
                    parts = candidates[0].get('content', {}).get('parts', [])
                    for part in parts:
                        if 'inlineData' in part:
                            audio_b64 = part['inlineData']['data']
                            return base64.b64decode(audio_b64)
        except Exception:
            pass

    # 2. OpenAI TTS
    o_key = _openai_key()
    if o_key:
        try:
            url = "https://api.openai.com/v1/audio/speech"
            headers = {
                "Authorization": f"Bearer {o_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "tts-1",
                "input": cleaned_text,
                "voice": "alloy",
                "response_format": "mp3"
            }
            r = requests.post(url, headers=headers, json=payload, timeout=10)
            if r.status_code == 200:
                return r.content
        except Exception:
            pass

    # 3. Fallback
    return None
