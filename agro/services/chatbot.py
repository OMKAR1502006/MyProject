"""
AgroSathi AI chatbot — Gemini (primary), OpenAI (fallback).
Re-exports core chat logic and adds live weather/mandi context for connected advice.
"""

from __future__ import annotations

from typing import Optional

from .chat import (
    ChatServiceError,
    build_system_prompt,
    check_rate_limit,
    get_ai_reply,
)
from .market import MarketServiceError, fetch_market_prices
from .weather import WeatherServiceError, fetch_weather

__all__ = [
    'ChatServiceError',
    'build_system_prompt',
    'check_rate_limit',
    'get_ai_reply',
    'get_chat_reply',
]


def _safe_weather_snippet(*, city: str, district: str, state: str) -> str:
    loc = district or state or city or 'Pune'
    try:
        data = fetch_weather(city=loc, language_code='en')
        cur = data.get('current') or {}
        return (
            f"Weather ({data.get('city', loc)}): {cur.get('temp')}°C, "
            f"{cur.get('weather')}, humidity {cur.get('humidity')}%, "
            f"wind {cur.get('wind_speed')} m/s. Source: {data.get('source')}."
        )
    except (WeatherServiceError, Exception):
        return ''


def _safe_market_snippet(*, crop: str, state: str) -> str:
    if not crop:
        crop = 'Wheat'
    if not state:
        state = 'Maharashtra'
    try:
        data = fetch_market_prices(crop=crop, state=state, limit=3, page=1, language_code='en')
        lines = []
        for r in data.get('records', [])[:3]:
            lines.append(
                f"{r.get('crop')} @ {r.get('market')}: ₹{r.get('modal_price')}/quintal"
            )
        if lines:
            return 'Recent mandi: ' + '; '.join(lines) + f" ({data.get('source')})."
    except (MarketServiceError, Exception):
        pass
    return ''


def build_enriched_system_prompt(
    *,
    language_code: str,
    farmer_context: dict,
    include_live_data: bool = True,
    detected_language_name: str = 'English',
) -> str:
    """System prompt with optional live weather and mandi context."""
    base = build_system_prompt(language_code=language_code, farmer_context=farmer_context)
    
    # Inject mandatory same-language system instruction at the very beginning
    same_lang_instruction = (
        "You are AgroSathi AI.\n\n"
        "Always answer in the SAME language used by the farmer.\n\n"
        f"Detected Language: {detected_language_name}\n\n"
        "Rules:\n\n"
        "Kannada → Kannada response\n"
        "Hindi → Hindi response\n"
        "Marathi → Marathi response\n"
        "Telugu → Telugu response\n"
        "English → English response\n\n"
        "Never switch language unless farmer requests translation.\n\n"
        "========================================\n\n"
    )
    base = same_lang_instruction + base

    if not include_live_data:
        return base

    ctx = farmer_context or {}
    extras = []
    weather_line = _safe_weather_snippet(
        city=ctx.get('district') or '',
        district=ctx.get('district') or '',
        state=ctx.get('state') or '',
    )
    if weather_line:
        extras.append(weather_line)
    market_line = _safe_market_snippet(
        crop=ctx.get('primary_crop') or 'Wheat',
        state=ctx.get('state') or 'Maharashtra',
    )
    if market_line:
        extras.append(market_line)

    if extras:
        base += '\n\nLive platform data for this farmer:\n' + '\n'.join(extras)
    return base


def _image_b64(image_file, image_bytes) -> tuple[Optional[str], str]:
    import base64

    mime = 'image/jpeg'
    if image_bytes:
        return base64.b64encode(image_bytes).decode('ascii'), mime
    if image_file:
        raw = image_file.read()
        mime = getattr(image_file, 'content_type', None) or mime
        return base64.b64encode(raw).decode('ascii'), mime
    return None, mime


def get_chat_reply(
    *,
    message: str,
    language_code: str = 'en',
    farmer_context: Optional[dict] = None,
    history: Optional[list[dict]] = None,
    image_file=None,
    image_bytes: Optional[bytes] = None,
    image_mime: str = 'image/jpeg',
    use_live_context: bool = True,
) -> tuple[str, str]:
    """
    Returns (reply_text, provider_name).
    Uses enriched context when Gemini/OpenAI is available.
    """
    from . import chat as chat_mod
    from .language_detector import detect_language

    message = (message or '').strip()
    if not message and not image_file and not image_bytes:
        raise ChatServiceError('Please enter a message or upload an image.', status=400)

    # Detect language of the input message
    detected = detect_language(message, browser_lang=language_code)
    detected_lang_name = detected['language']
    detected_lang_code = detected['code']

    system_prompt = build_enriched_system_prompt(
        language_code=detected_lang_code,
        farmer_context=farmer_context or {},
        include_live_data=use_live_context,
        detected_language_name=detected_lang_name,
    )

    history = history or []
    image_b64, mime = _image_b64(image_file, image_bytes)
    if image_b64:
        image_mime = mime

    if chat_mod._gemini_key():
        try:
            reply = chat_mod._call_gemini(
                message=message,
                system_prompt=system_prompt,
                history=history,
                image_b64=image_b64,
                image_mime=image_mime,
            )
            return reply, 'gemini'
        except ChatServiceError:
            if not chat_mod._openai_key():
                raise

    if chat_mod._openai_key():
        if image_b64:
            raise ChatServiceError(
                'Image analysis requires GEMINI_API_KEY in .env.',
                status=400,
            )
        reply = chat_mod._call_openai(
            message=message,
            system_prompt=system_prompt,
            history=history,
        )
        return reply, 'openai'

    return chat_mod._rule_based_reply(message, detected_lang_code), 'fallback'

