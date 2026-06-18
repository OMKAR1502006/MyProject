"""
AI farming chatbot — Gemini (primary) or OpenAI (fallback).
API keys stay server-side only.
"""

import base64
import os
import time
from typing import Optional

import requests
from django.conf import settings
from django.core.cache import cache

LANGUAGE_NAMES = {
    'en': 'English',
    'hi': 'Hindi (Devanagari script)',
    'mr': 'Marathi (Devanagari script)',
    'te': 'Telugu script',
    'kn': 'Kannada script',
}

SYSTEM_PROMPT_TEMPLATE = """You are AgroSathi, a helpful AI farming assistant for Indian farmers.
Answer in {language_name} only. Keep answers practical, short (under 200 words unless asked for detail),
and focused on Indian agriculture context (crops, seasons, mandi, monsoon).

You help with: crop diseases, fertilizers, irrigation, weather decisions, pest control, soil health, and market selling tips.
If unsure, say so and suggest consulting a local Krishi Vigyan Kendra (KVK) or agriculture officer.
Never make up pesticide doses — give general guidance and advise reading product labels.

Farmer context:
- Name: {farmer_name}
- Location: {village}, {district}, {state}
- Primary crop: {primary_crop}
- Farm size: {farm_size} acres
"""


class ChatServiceError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


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


def _timeout() -> int:
    return int(getattr(settings, 'CHAT_API_TIMEOUT', 45))


def _rate_limit_per_hour() -> int:
    return int(getattr(settings, 'CHAT_RATE_LIMIT_PER_HOUR', 30))


def check_rate_limit(user_id: int) -> None:
    """Per-user hourly rate limit via Django cache."""
    key = f'chat_rate:{user_id}'
    now = time.time()
    window = 3600
    bucket = cache.get(key) or []
    bucket = [t for t in bucket if now - t < window]
    if len(bucket) >= _rate_limit_per_hour():
        raise ChatServiceError(
            'Too many messages. Please wait a while before sending more.',
            status=429,
        )
    bucket.append(now)
    cache.set(key, bucket, timeout=window)


def build_system_prompt(*, language_code: str, farmer_context: dict) -> str:
    lang = (language_code or 'en').split('-')[0]
    ctx = farmer_context or {}
    farm_size = ctx.get('farm_size_acres')
    farm_str = str(farm_size) if farm_size is not None else 'not specified'
    return SYSTEM_PROMPT_TEMPLATE.format(
        language_name=LANGUAGE_NAMES.get(lang, 'English'),
        farmer_name=ctx.get('name') or 'Farmer',
        village=ctx.get('village') or '—',
        district=ctx.get('district') or '—',
        state=ctx.get('state') or 'India',
        primary_crop=ctx.get('primary_crop') or 'mixed crops',
        farm_size=farm_str,
    )


def _rule_based_reply(message: str, language_code: str) -> str:
    """Keyword-based farming assistant when no AI API key is set."""
    lang = (language_code or 'en').split('-')[0]
    msg = (message or '').lower()

    def pick(en: str, hi: str, mr: str, te: str, kn: str = '') -> str:
        return {'en': en, 'hi': hi, 'mr': mr, 'te': te, 'kn': kn or en}.get(lang, en)

    if any(w in msg for w in ('disease', 'blight', 'pest', 'leaf', 'रोग', 'कीड')):
        return pick(
            'For crop disease: upload a clear leaf photo under Disease Detection. '
            'Remove infected leaves, avoid overhead irrigation, and consult your local KVK for fungicide doses.',
            'फसल रोग: Disease Detection में पत्ती की फोटो अपलोड करें। संक्रमित पत्ते हटाएँ, छिड़काव सिंचाई से बचें, KVK से सलाह लें।',
            'पीक रोग: Disease Detection मध्ये पानाचा फोटो अपलोड करा. संक्रमित पाने काढा, शिफारसीनुसार फवारणी करा.',
            'పంట వ్యాధి: Disease Detectionలో ఆకు ఫోటో అప్‌లోడ్ చేయండి. సంక్రమిత ఆకులు తొలగించండి, KVK సలహా తీసుకోండి.',
            'ಬೆಳೆ ರೋಗ: Disease Detection ನಲ್ಲಿ ಎಲೆಯ ಫೋಟೋ ಅಪ್‌ಲೋಡ್ ಮಾಡಿ. ಸೋಂಕಿತ ಎಲೆ ತೆಗೆಯಿರಿ, KVK ಸಲಹೆ ತೆಗೆದುಕೊಳ್ಳಿ.',
        )
    if any(w in msg for w in ('weather', 'rain', 'मौसम', 'पाऊस', 'వర్ష')):
        return pick(
            'Open the Weather page for live temperature, rain, and 5-day forecast for your location.',
            'मौसम पेज पर जाएँ — तापमान, बारिश और 5 दिन का पूर्वानुमान मिलेगा।',
            'Weather पेजवर जा — थेट हवामान आणि 5 दिवसांचा अंदाज.',
            'Weather పేజీలో ప్రస్తుత వాతావరణం మరియు 5 రోజుల సూచన చూడండి.',
            'Weather ಪುಟದಲ್ಲಿ ತಾಪಮಾನ, ಮಳೆ ಮತ್ತು 5 ದಿನದ ಮುನ್ಸೂಚನೆ ನೋಡಿ.',
        )
    if any(w in msg for w in ('price', 'mandi', 'market', 'भाव', 'मंडी', 'ధర')):
        return pick(
            'Check Mandi Prices to search crop rates by state and district. Add AGMARKNET_API_KEY in .env for government live data.',
            'Mandi Prices में फसल के भाव खोजें। लाइव डेटा के लिए .env में AGMARKNET_API_KEY जोड़ें।',
            'Mandi Prices मध्ये भाव शोधा. लाइव डेटासाठी AGMARKNET_API_KEY वापरा.',
            'Mandi Pricesలో మండి ధరలు చూడండి. లైవ్ డేటా కోసం AGMARKNET_API_KEY జోడించండి.',
            'Mandi Prices ನಲ್ಲಿ ಬೆಲೆ ಹುಡುಕಿ. ಲೈವ್ ಡೇಟಾಕ್ಕೆ AGMARKNET_API_KEY ಸೇರಿಸಿ.',
        )
    if any(w in msg for w in ('fertilizer', 'npk', 'उर्वरक', 'खत')):
        return pick(
            'Soil test first (Soil Analysis page). Balance NPK per crop stage; split nitrogen applications; '
            'use organic manure where possible. Always follow product label doses.',
            'पहले मिट्टी जाँच करें (Soil Analysis)। NPK संतुलन रखें; नाइट्रोजन विभाजित करें; लेबल अनुसार मात्रा लें।',
            'प्रथम माती तपासणी करा. NPK समतोल ठेवा; लेबलनुसार डोस घ्या.',
            'మొదట నేల విశ్లేషణ చేయండి. NPK సమతుల్యం పాటించండి; లేబుల్ ప్రకారం మోతాదు వాడండి.',
            'ಮೊದಲು Soil Analysis ಮಾಡಿ. NPK ಸಮತೋಲನ ಇರಿಸಿ; ಲೇಬಲ್ ಪ್ರಕಾರ ಮೋತಾದ.',
        )
    if any(w in msg for w in ('irrigation', 'water', 'सिंचाई', 'पाणी')):
        return pick(
            'Irrigate early morning or evening to reduce evaporation. Check Weather for rain forecast before scheduling irrigation.',
            'सुबह या शाम को सिंचाई करें। सिंचाई से पहले Weather में बारिश पूर्वानुमान देखें।',
            'सकाळी किंवा संध्याकाळी सिंचन करा. पाऊस अंदाजासाठी Weather पहा.',
            'ఉదయం లేదా సాయంత్రం నీటి పారుదల చేయండి. వర్ష సూచన కోసం Weather చూడండి.',
            'ಬೆಳಿಗ್ಗೆ ಅಥವಾ ಸಂಜೆ ನೀರಾವರಿ ಮಾಡಿ. ಮಳೆ ಮುನ್ಸೂಚನೆಗೆ Weather ನೋಡಿ.',
        )

    return pick(
        'AgroSathi tip: add GEMINI_API_KEY in .env for full AI answers. '
        'Use Dashboard links for Weather, Mandi Prices, Disease Detection, Soil Analysis, and Schemes.',
        'पूर्ण AI के लिए .env में GEMINI_API_KEY जोड़ें। Dashboard से Weather, Mandi, Disease, Soil उपयोग करें।',
        'पूर्ण AI साठी .env मध्ये GEMINI_API_KEY जोडा. Dashboard वरून सर्व सुविधा वापरा.',
        'పూర్తి AI కోసం .env లో GEMINI_API_KEY జోడించండి. Dashboard నుండి అన్ని ఫీచర్లు వాడండి.',
        'ಪೂರ್ಣ AI ಗೆ .env ನಲ್ಲಿ GEMINI_API_KEY ಸೇರಿಸಿ. Dashboard ನಿಂದ ಎಲ್ಲಾ ಫೀಚರ್ ಬಳಸಿ.',
    )


def _call_gemini_sdk(
    *,
    message: str,
    system_prompt: str,
    history: list[dict],
    image_b64: Optional[str] = None,
    image_mime: str = 'image/jpeg',
) -> str:
    """Primary path: official google-generativeai Python SDK."""
    api_key = _gemini_key()
    if not api_key:
        raise ChatServiceError('Gemini API key not configured', status=503)

    try:
        import google.generativeai as genai  # noqa: PLC0415
    except ImportError:
        raise ChatServiceError('google-generativeai package not installed', status=503)

    genai.configure(api_key=api_key)
    model_name = getattr(settings, 'GEMINI_MODEL', 'gemini-1.5-flash')
    model = genai.GenerativeModel(model_name, system_instruction=system_prompt)

    chat_history = []
    for turn in history[-6:]:
        role = 'user' if turn.get('role') == 'user' else 'model'
        chat_history.append({'role': role, 'parts': [turn.get('content', '')]})

    parts = [message]
    if image_b64:
        parts.append({'mime_type': image_mime, 'data': base64.b64decode(image_b64)})

    try:
        if chat_history:
            chat = model.start_chat(history=chat_history)
            response = chat.send_message(parts)
        else:
            response = model.generate_content(parts)
        reply = (response.text or '').strip()
        if reply:
            return reply
    except Exception as exc:
        raise ChatServiceError(f'Gemini SDK error: {exc}', status=502) from exc

    raise ChatServiceError('Empty response from Gemini', status=502)


def _call_gemini_rest(
    *,
    message: str,
    system_prompt: str,
    history: list[dict],
    image_b64: Optional[str] = None,
    image_mime: str = 'image/jpeg',
) -> str:
    """REST fallback when SDK fails."""
    api_key = _gemini_key()
    if not api_key:
        raise ChatServiceError('Gemini API key not configured', status=503)

    models = [
        getattr(settings, 'GEMINI_MODEL', 'gemini-1.5-flash'),
        'gemini-1.5-flash-latest',
        'gemini-1.5-flash',
        'gemini-2.0-flash',
    ]

    contents = []
    for turn in history[-6:]:
        role = 'user' if turn.get('role') == 'user' else 'model'
        contents.append({
            'role': role,
            'parts': [{'text': turn.get('content', '')}],
        })

    user_parts = [{'text': message}]
    if image_b64:
        user_parts.append({
            'inline_data': {'mime_type': image_mime, 'data': image_b64},
        })
    contents.append({'role': 'user', 'parts': user_parts})

    payload = {
        'systemInstruction': {'parts': [{'text': system_prompt}]},
        'contents': contents,
        'generationConfig': {
            'temperature': 0.7,
            'maxOutputTokens': 1024,
        },
    }

    headers = {
        'x-goog-api-key': api_key,
        'Content-Type': 'application/json'
    }

    last_status = 502
    last_detail = ''
    for model in models:
        url = (
            f'https://generativelanguage.googleapis.com/v1beta/models/'
            f'{model}:generateContent'
        )
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=_timeout())
        except requests.Timeout:
            raise ChatServiceError('AI service timed out. Please try again.', status=504)
        except requests.RequestException as exc:
            raise ChatServiceError(f'AI service error: {exc}', status=502)

        if resp.status_code != 200:
            last_status = resp.status_code
            last_detail = resp.text[:200]
            continue

        data = resp.json()
        candidates = data.get('candidates') or []
        if not candidates:
            continue

        parts_out = candidates[0].get('content', {}).get('parts') or []
        text_parts = [p.get('text', '') for p in parts_out if p.get('text')]
        reply = ''.join(text_parts).strip()
        if reply:
            return reply

    raise ChatServiceError(
        f'Gemini API error ({last_status})' + (f': {last_detail}' if last_detail else ''),
        status=502,
    )


def _call_gemini(
    *,
    message: str,
    system_prompt: str,
    history: list[dict],
    image_b64: Optional[str] = None,
    image_mime: str = 'image/jpeg',
) -> str:
    try:
        return _call_gemini_sdk(
            message=message,
            system_prompt=system_prompt,
            history=history,
            image_b64=image_b64,
            image_mime=image_mime,
        )
    except (ChatServiceError, Exception):
        return _call_gemini_rest(
            message=message,
            system_prompt=system_prompt,
            history=history,
            image_b64=image_b64,
            image_mime=image_mime,
        )


def _call_openai(
    *,
    message: str,
    system_prompt: str,
    history: list[dict],
) -> str:
    api_key = _openai_key()
    if not api_key:
        raise ChatServiceError('OpenAI API key not configured', status=503)

    model = getattr(settings, 'OPENAI_CHAT_MODEL', 'gpt-4o-mini')
    messages = [{'role': 'system', 'content': system_prompt}]
    for turn in history[-8:]:
        role = 'user' if turn.get('role') == 'user' else 'assistant'
        messages.append({'role': role, 'content': turn.get('content', '')})
    messages.append({'role': 'user', 'content': message})

    try:
        resp = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            json={
                'model': model,
                'messages': messages,
                'max_tokens': 1024,
                'temperature': 0.7,
            },
            timeout=_timeout(),
        )
    except requests.Timeout:
        raise ChatServiceError('AI service timed out. Please try again.', status=504)
    except requests.RequestException as exc:
        raise ChatServiceError(f'AI service error: {exc}', status=502)

    if resp.status_code != 200:
        raise ChatServiceError(
            f'OpenAI API error ({resp.status_code})',
            status=502,
        )

    data = resp.json()
    choices = data.get('choices') or []
    if not choices:
        raise ChatServiceError('Empty response from AI', status=502)
    reply = (choices[0].get('message') or {}).get('content', '').strip()
    if not reply:
        raise ChatServiceError('Empty response from AI', status=502)
    return reply


def get_ai_reply(
    *,
    message: str,
    language_code: str = 'en',
    farmer_context: Optional[dict] = None,
    history: Optional[list[dict]] = None,
    image_file=None,
    image_bytes: Optional[bytes] = None,
    image_mime: str = 'image/jpeg',
) -> tuple[str, str]:
    """
    Returns (reply_text, provider_name).
    provider: gemini | openai | fallback
    """
    message = (message or '').strip()
    if not message and not image_file and not image_bytes:
        raise ChatServiceError('Please enter a message or upload an image.', status=400)
    if len(message) > 4000:
        raise ChatServiceError('Message is too long (max 4000 characters).', status=400)

    system_prompt = build_system_prompt(
        language_code=language_code,
        farmer_context=farmer_context or {},
    )
    history = history or []

    image_b64 = None
    if image_bytes:
        image_b64 = base64.b64encode(image_bytes).decode('ascii')
    elif image_file:
        raw = image_file.read()
        image_b64 = base64.b64encode(raw).decode('ascii')
        image_mime = getattr(image_file, 'content_type', None) or image_mime

    if image_b64 and not message:
        message = 'Please analyze this crop/plant image for disease or health issues and advise treatment.'

    import logging
    logger = logging.getLogger(__name__)

    if _gemini_key():
        try:
            reply = _call_gemini(
                message=message,
                system_prompt=system_prompt,
                history=history,
                image_b64=image_b64,
                image_mime=image_mime,
            )
            return reply, 'gemini'
        except Exception as exc:
            logger.error(f"Gemini API error (falling back): {exc}", exc_info=True)

    if _openai_key() and not image_b64:
        try:
            reply = _call_openai(
                message=message,
                system_prompt=system_prompt,
                history=history,
            )
            return reply, 'openai'
        except Exception as exc:
            logger.error(f"OpenAI API error (falling back to rule-based): {exc}", exc_info=True)

    return _rule_based_reply(message, language_code), 'fallback'
