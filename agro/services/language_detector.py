import re
import os
from typing import Dict, Optional
from django.conf import settings

def detect_language(text: str, browser_lang: Optional[str] = None) -> Dict[str, str]:
    """
    Detects the language of the given text.
    Priority:
    1. Unicode script detection
    2. Browser language
    3. LLM fallback
    """
    text = (text or "").strip()
    
    # 1. Unicode script detection
    # Kannada: [\u0C80-\u0CFF]
    if re.search(r'[\u0C80-\u0CFF]', text):
        return {"language": "Kannada", "code": "kn"}
        
    # Telugu: [\u0C00-\u0C7F]
    if re.search(r'[\u0C00-\u0C7F]', text):
        return {"language": "Telugu", "code": "te"}
        
    # Devanagari range: [\u0900-\u097F] (Hindi and Marathi)
    if re.search(r'[\u0900-\u097F]', text):
        # Distinguish using langdetect if installed
        try:
            import langdetect
            detected = langdetect.detect(text)
            if detected == 'mr':
                return {"language": "Marathi", "code": "mr"}
            elif detected == 'hi':
                return {"language": "Hindi", "code": "hi"}
        except Exception:
            pass
            
        # Fallback to browser language
        if browser_lang:
            lang_clean = browser_lang.lower().split('-')[0]
            if lang_clean == 'mr':
                return {"language": "Marathi", "code": "mr"}
            elif lang_clean == 'hi':
                return {"language": "Hindi", "code": "hi"}
                
        # Default Devanagari to Hindi
        return {"language": "Hindi", "code": "hi"}

    # English / ASCII checks (contains standard alphabets and matches English characteristics)
    # If it's pure ASCII characters (with letters)
    if re.search(r'[a-zA-Z]', text) and all(ord(c) < 128 for c in text if c.isalpha()):
        return {"language": "English", "code": "en"}

    # 2. Browser language fallback
    if browser_lang:
        lang_clean = browser_lang.lower().split('-')[0]
        mapping = {
            'kn': ("Kannada", "kn"),
            'te': ("Telugu", "te"),
            'hi': ("Hindi", "hi"),
            'mr': ("Marathi", "mr"),
            'en': ("English", "en")
        }
        if lang_clean in mapping:
            name, code = mapping[lang_clean]
            return {"language": name, "code": code}

    # 3. LLM fallback (if API key is available)
    gemini_key = os.getenv('GEMINI_API_KEY') or getattr(settings, 'GEMINI_API_KEY', None)
    openai_key = os.getenv('OPENAI_API_KEY') or getattr(settings, 'OPENAI_API_KEY', None)
    
    if text and (gemini_key or openai_key):
        prompt = (
            "Identify the language of the following text. "
            "Respond with exactly one of these words: Kannada, Hindi, Marathi, Telugu, English. "
            "Do not include any other text or punctuation. "
            f"Text: {text}"
        )
        
        # Try Gemini
        if gemini_key:
            try:
                import requests
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
                payload = {"contents": [{"parts": [{"text": prompt}]}]}
                r = requests.post(url, json=payload, timeout=5)
                if r.status_code == 200:
                    ans = r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
                    mapping = {
                        "kannada": ("Kannada", "kn"),
                        "telugu": ("Telugu", "te"),
                        "hindi": ("Hindi", "hi"),
                        "marathi": ("Marathi", "mr"),
                        "english": ("English", "en")
                    }
                    ans_lower = ans.lower()
                    if ans_lower in mapping:
                        name, code = mapping[ans_lower]
                        return {"language": name, "code": code}
            except Exception:
                pass
                
        # Try OpenAI
        if openai_key:
            try:
                import requests
                headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
                payload = {
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 10
                }
                r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=5)
                if r.status_code == 200:
                    ans = r.json()['choices'][0]['message']['content'].strip()
                    mapping = {
                        "kannada": ("Kannada", "kn"),
                        "telugu": ("Telugu", "te"),
                        "hindi": ("Hindi", "hi"),
                        "marathi": ("Marathi", "mr"),
                        "english": ("English", "en")
                    }
                    ans_lower = ans.lower()
                    if ans_lower in mapping:
                        name, code = mapping[ans_lower]
                        return {"language": name, "code": code}
            except Exception:
                pass

    # Default fallback
    return {"language": "English", "code": "en"}
