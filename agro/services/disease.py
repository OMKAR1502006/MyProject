"""
Plant disease detection — Gemini Vision (primary), optional TensorFlow model, heuristic fallback.
"""

import base64
import json
import logging
import os
import re
from pathlib import Path
from typing import Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

LABELS_PATH = Path(__file__).resolve().parent.parent / 'data' / 'plant_disease_labels.json'
DEFAULT_MODEL_PATH = Path(__file__).resolve().parent.parent / 'ml' / 'models' / 'plant_disease_mobilenet.keras'

_TENSORFLOW_MODEL = None
_LABELS: list[str] | None = None

TREATMENT_DB = {
    'healthy': [
        'Continue regular monitoring and balanced fertilization.',
        'Maintain proper irrigation and pest scouting schedule.',
    ],
    'leaf blight': [
        'Apply Mancozeb 75% WP @ 2 g/L or valid copper fungicide per label.',
        'Remove heavily infected leaves and destroy away from field.',
        'Avoid overhead irrigation; improve airflow between rows.',
        'Repeat spray after 10–14 days if symptoms persist.',
    ],
    'powdery mildew': [
        'Spray sulfur 80% WP or potassium bicarbonate per label rates.',
        'Reduce nitrogen; avoid dense canopy humidity.',
        'Remove infected plant parts early.',
    ],
    'rust': [
        'Use Propiconazole or Tebuconazole as per local agri officer advice.',
        'Remove infected debris after harvest.',
        'Use resistant varieties where available.',
    ],
    'bacterial spot': [
        'Copper-based bactericide spray; avoid working wet fields.',
        'Use certified disease-free seed.',
        'Rotate crops and manage plant debris.',
    ],
    'early blight': [
        'Chlorothalonil or Mancozeb spray at recommended intervals.',
        'Mulch soil to reduce spore splash.',
        'Ensure balanced potassium nutrition.',
    ],
    'late blight': [
        'Metalaxyl + Mancozeb combination per label (emergency spray).',
        'Destroy infected plants immediately in severe cases.',
        'Avoid irrigation during cool humid evenings.',
    ],
}


class DiseaseServiceError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


def _load_labels() -> list[str]:
    global _LABELS
    if _LABELS is not None:
        return _LABELS
    if LABELS_PATH.exists():
        with open(LABELS_PATH, encoding='utf-8') as f:
            data = json.load(f)
        _LABELS = data.get('labels', [])
    else:
        _LABELS = [
            'Healthy', 'Leaf Blight', 'Powdery Mildew', 'Rust', 'Bacterial Spot',
            'Early Blight', 'Late Blight',
        ]
    return _LABELS


def _treatment_for(disease: str) -> list[str]:
    key = disease.lower().strip()
    for k, steps in TREATMENT_DB.items():
        if k in key or key in k:
            return steps
    return [
        'Consult local Krishi Vigyan Kendra (KVK) for confirmed diagnosis.',
        'Follow label directions for any fungicide or pesticide application.',
        'Take a clear photo of affected leaves and share with extension officer.',
    ]


def _gemini_key() -> Optional[str]:
    return os.getenv('GEMINI_API_KEY') or getattr(settings, 'GEMINI_API_KEY', None)


def _parse_gemini_json(text: str) -> dict:
    text = text.strip()
    if text.startswith('```'):
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
    data = json.loads(text)
    preds = data.get('predictions') or []
    if not preds and data.get('disease'):
        preds = [{'disease': data['disease'], 'probability': data.get('confidence', 0.8)}]
    disease = preds[0]['disease'] if preds else data.get('disease', 'Unknown')
    conf = float(preds[0].get('probability', data.get('confidence', 0.5)))
    solution = data.get('top_solution') or _treatment_for(disease)
    return {
        'source': 'gemini',
        'predictions': preds[:5],
        'top_solution': solution,
        'confidence': conf,
        'disease': disease,
    }


def _predict_gemini_sdk(image_bytes: bytes, mime: str) -> dict:
    api_key = _gemini_key()
    if not api_key:
        raise DiseaseServiceError('Gemini API key not configured', status=503)

    try:
        import google.generativeai as genai  # noqa: PLC0415
        from PIL import Image  # noqa: PLC0415
        import io
    except ImportError as exc:
        raise DiseaseServiceError(f'Missing package: {exc}', status=503) from exc

    genai.configure(api_key=api_key)
    model_name = getattr(settings, 'GEMINI_MODEL', 'gemini-1.5-flash')
    model = genai.GenerativeModel(model_name)
    img = Image.open(io.BytesIO(image_bytes))
    prompt = (
        'You are an agricultural plant pathologist for Indian farmers. '
        'Analyze this crop/plant leaf image. Reply with ONLY valid JSON (no markdown): '
        '{"disease":"<name>","confidence":0.0-1.0,'
        '"predictions":[{"disease":"<name>","probability":0.0-1.0}],'
        '"top_solution":["step1","step2"]}. '
        'Include 3 predictions sorted by probability. Use common disease names.'
    )
    response = model.generate_content([prompt, img])
    text = (response.text or '').strip()
    if not text:
        raise DiseaseServiceError('Empty response from Gemini', status=502)
    try:
        return _parse_gemini_json(text)
    except json.JSONDecodeError as exc:
        raise DiseaseServiceError('Invalid JSON from AI', status=502) from exc


def _predict_gemini_rest(image_bytes: bytes, mime: str) -> dict:
    api_key = _gemini_key()
    if not api_key:
        raise DiseaseServiceError('Gemini API key not configured', status=503)

    models = [
        getattr(settings, 'GEMINI_MODEL', 'gemini-1.5-flash'),
        'gemini-1.5-flash-latest',
        'gemini-1.5-flash',
        'gemini-2.0-flash',
    ]
    b64 = base64.b64encode(image_bytes).decode('ascii')
    prompt = (
        'You are an agricultural plant pathologist for Indian farmers. '
        'Analyze this crop/plant leaf image. Reply with ONLY valid JSON (no markdown): '
        '{"disease":"<name>","confidence":0.0-1.0,'
        '"predictions":[{"disease":"<name>","probability":0.0-1.0}],'
        '"top_solution":["step1","step2"]}. '
        'Include 3 predictions sorted by probability. Use common disease names.'
    )

    last_err = None
    for model in models:
        url = (
            f'https://generativelanguage.googleapis.com/v1beta/models/'
            f'{model}:generateContent?key={api_key}'
        )
        payload = {
            'contents': [{
                'parts': [
                    {'text': prompt},
                    {'inline_data': {'mime_type': mime, 'data': b64}},
                ],
            }],
            'generationConfig': {'temperature': 0.2, 'maxOutputTokens': 1024},
        }
        try:
            resp = requests.post(url, json=payload, timeout=int(getattr(settings, 'CHAT_API_TIMEOUT', 45)))
            if resp.status_code != 200:
                last_err = resp.text[:300]
                continue
            text = ''
            for part in (resp.json().get('candidates') or [{}])[0].get('content', {}).get('parts', []):
                text += part.get('text', '')
            text = text.strip()
            if text.startswith('```'):
                text = re.sub(r'^```(?:json)?\s*', '', text)
                text = re.sub(r'\s*```$', '', text)
            return _parse_gemini_json(text)
        except json.JSONDecodeError:
            last_err = 'Invalid JSON from AI'
        except requests.RequestException as exc:
            last_err = str(exc)

    raise DiseaseServiceError(f'AI disease analysis failed: {last_err or "unknown"}', status=502)


def _predict_gemini(image_bytes: bytes, mime: str) -> dict:
    try:
        return _predict_gemini_sdk(image_bytes, mime)
    except (DiseaseServiceError, Exception):
        return _predict_gemini_rest(image_bytes, mime)


def _load_tf_model():
    global _TENSORFLOW_MODEL
    if _TENSORFLOW_MODEL is not None:
        return _TENSORFLOW_MODEL

    model_path = os.getenv('DISEASE_MODEL_PATH', '')
    if not model_path:
        model_path = str(getattr(settings, 'DISEASE_MODEL_PATH', DEFAULT_MODEL_PATH))
    path = Path(model_path)
    if not path.exists():
        return None

    try:
        import tensorflow as tf  # noqa: PLC0415
        _TENSORFLOW_MODEL = tf.keras.models.load_model(path)
        return _TENSORFLOW_MODEL
    except ImportError:
        return None
    except Exception:
        return None


def _predict_tensorflow(image_bytes: bytes) -> dict:
    model = _load_tf_model()
    if model is None:
        raise DiseaseServiceError('TensorFlow model not available', status=503)

    try:
        import numpy as np  # noqa: PLC0415
        from PIL import Image  # noqa: PLC0415
        import io

        img = Image.open(io.BytesIO(image_bytes)).convert('RGB').resize((224, 224))
        arr = np.array(img, dtype=np.float32) / 255.0
        batch = np.expand_dims(arr, axis=0)
        preds = model.predict(batch, verbose=0)[0]
        labels = _load_labels()
        if len(labels) != len(preds):
            labels = [f'Class_{i}' for i in range(len(preds))]

        ranked = sorted(
            [{'disease': labels[i], 'probability': float(preds[i])} for i in range(len(preds))],
            key=lambda x: x['probability'],
            reverse=True,
        )[:5]
        total = sum(p['probability'] for p in ranked) or 1.0
        ranked = [
            {'disease': p['disease'], 'probability': round(p['probability'] / total, 4)}
            for p in ranked
        ]
        top = ranked[0]
        return {
            'source': 'tensorflow',
            'predictions': ranked,
            'top_solution': _treatment_for(top['disease']),
            'confidence': top['probability'],
            'disease': top['disease'],
        }
    except Exception as exc:
        raise DiseaseServiceError(f'Model inference failed: {exc}', status=500)


def _predict_heuristic(image_bytes: bytes) -> dict:
    """Image analysis when no API key / model — not random mock; uses color features."""
    from PIL import Image
    import io

    img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    img.thumbnail((256, 256))
    pixels = list(img.getdata())
    r = sum(p[0] for p in pixels) / len(pixels)
    g = sum(p[1] for p in pixels) / len(pixels)
    b = sum(p[2] for p in pixels) / len(pixels)

    if g > r + 15 and g > b + 10:
        disease, conf = 'Healthy', 0.62
    elif r > g + 25:
        disease, conf = 'Leaf Blight', 0.58
    elif r > 180 and g > 160 and b > 140:
        disease, conf = 'Powdery Mildew', 0.55
    elif r < 100 and g < 120:
        disease, conf = 'Rust', 0.52
    else:
        disease, conf = 'Bacterial Spot', 0.50

    preds = [
        {'disease': disease, 'probability': conf},
        {'disease': 'Healthy' if disease != 'Healthy' else 'Leaf Blight', 'probability': round(1 - conf - 0.1, 2)},
    ]
    return {
        'source': 'heuristic',
        'predictions': preds,
        'top_solution': _treatment_for(disease),
        'confidence': conf,
        'disease': disease,
        'note': 'Add GEMINI_API_KEY or place TensorFlow model for higher accuracy.',
    }

def _check_leaf_with_gemini_sdk(image_bytes: bytes, mime: str) -> bool:
    api_key = _gemini_key()
    if not api_key:
        raise Exception("No Gemini API key")

    try:
        import google.generativeai as genai
        from PIL import Image
        import io
    except ImportError as exc:
        raise Exception(f"Missing package: {exc}") from exc

    genai.configure(api_key=api_key)
    model_name = getattr(settings, 'GEMINI_MODEL', 'gemini-1.5-flash')
    model = genai.GenerativeModel(model_name)
    img = Image.open(io.BytesIO(image_bytes))

    prompt = (
        "Analyze this image. Determine if it contains a plant leaf, crop leaf, or tree leaf. "
        "A valid image contains a real plant or crop leaf (e.g., tomato, potato, rice, corn, maize, wheat, or general crop/plant leaves). "
        "An invalid image contains screenshots, documents, text, websites, human faces, animals, vehicles, buildings, random objects, "
        "mobile/computer screenshots, or anything that is not a real plant/crop leaf. "
        "Respond with ONLY valid JSON (no markdown): "
        '{"is_leaf": true/false, "confidence": 0.0-1.0}'
    )

    response = model.generate_content([prompt, img])
    text = (response.text or '').strip()
    if not text:
        raise Exception("Empty response from Gemini")

    if text.startswith('```'):
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise Exception("Invalid JSON response from Gemini") from exc

    is_leaf = bool(data.get('is_leaf', False))
    confidence = float(data.get('confidence', 0.0))

    if not is_leaf:
        return False
    if confidence < 0.70:
        return False
    return True


def _check_leaf_with_gemini_rest(image_bytes: bytes, mime: str) -> bool:
    api_key = _gemini_key()
    if not api_key:
        raise Exception("No Gemini API key")

    models = [
        getattr(settings, 'GEMINI_MODEL', 'gemini-1.5-flash'),
        'gemini-1.5-flash-latest',
        'gemini-1.5-flash',
        'gemini-2.0-flash',
    ]
    b64 = base64.b64encode(image_bytes).decode('ascii')
    prompt = (
        "Analyze this image. Determine if it contains a plant leaf, crop leaf, or tree leaf. "
        "A valid image contains a real plant or crop leaf (e.g., tomato, potato, rice, corn, maize, wheat, or general crop/plant leaves). "
        "An invalid image contains screenshots, documents, text, websites, human faces, animals, vehicles, buildings, random objects, "
        "mobile/computer screenshots, or anything that is not a real plant/crop leaf. "
        "Respond with ONLY valid JSON (no markdown): "
        '{"is_leaf": true/false, "confidence": 0.0-1.0}'
    )

    last_err = None
    for model in models:
        url = (
            f'https://generativelanguage.googleapis.com/v1beta/models/'
            f'{model}:generateContent?key={api_key}'
        )
        payload = {
            'contents': [{
                'parts': [
                    {'text': prompt},
                    {'inline_data': {'mime_type': mime, 'data': b64}},
                ],
            }],
            'generationConfig': {'temperature': 0.1, 'maxOutputTokens': 128},
        }
        try:
            resp = requests.post(url, json=payload, timeout=15)
            if resp.status_code != 200:
                last_err = resp.text[:300]
                continue
            text = ''
            for part in (resp.json().get('candidates') or [{}])[0].get('content', {}).get('parts', []):
                text += part.get('text', '')
            text = text.strip()
            if text.startswith('```'):
                text = re.sub(r'^```(?:json)?\s*', '', text)
                text = re.sub(r'\s*```$', '', text)
            data = json.loads(text)
            is_leaf = bool(data.get('is_leaf', False))
            confidence = float(data.get('confidence', 0.0))
            if not is_leaf:
                return False
            if confidence < 0.70:
                return False
            return True
        except Exception as exc:
            last_err = str(exc)

    raise Exception(f"REST Gemini validation failed: {last_err}")


def _check_leaf_with_gemini(image_bytes: bytes, mime: str) -> bool:
    try:
        return _check_leaf_with_gemini_sdk(image_bytes, mime)
    except Exception:
        return _check_leaf_with_gemini_rest(image_bytes, mime)


def _check_leaf_with_cv(image_bytes: bytes) -> bool:
    try:
        from PIL import Image
        import io

        img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        img = img.resize((64, 64))
        pixels = list(img.getdata())
        total = len(pixels)

        white_count = 0
        black_count = 0
        leaf_count = 0

        for r, g, b in pixels:
            # White pixel (screenshot/document background)
            if r > 230 and g > 230 and b > 230:
                white_count += 1
            # Black pixel (dark mode background)
            elif r < 25 and g < 25 and b < 25:
                black_count += 1
            
            # Leaf color check (green or brown/yellow diseased colors)
            # Green leaf
            is_green = (g > r + 8) and (g > b + 8)
            # Yellow/brown leaf (e.g. blight, rust, spot, dry)
            is_yellow_brown = (r > 90) and (g > 75) and (b < 110) and (abs(r - g) < 45)
            
            if is_green or is_yellow_brown:
                leaf_count += 1

        white_pct = white_count / total
        black_pct = black_count / total
        leaf_pct = leaf_count / total

        # If it's mostly white/black (like document/screenshot)
        if white_pct > 0.40 or black_pct > 0.40 or (white_pct + black_pct) > 0.35:
            return False

        # If it doesn't have enough leaf pixels
        if leaf_pct < 0.25:
            return False

        return True
    except Exception as exc:
        logger.error(f"CV check exception: {exc}")
        # If processing fails (e.g., corrupted file), reject the image
        return False


def _validate_image_is_leaf(image_bytes: bytes, mime: str) -> bool:
    logger.info("Validation started")
    # 1. Try Gemini Vision if API key is configured
    if _gemini_key():
        try:
            logger.info("Attempting validation via Gemini")
            is_leaf = _check_leaf_with_gemini(image_bytes, mime)
            logger.info(f"Gemini validation result: {is_leaf}")
            return is_leaf
        except Exception as e:
            logger.warning(f"Gemini validation failed with error: {e}. Falling back to CV.")
            pass

    # 2. Fallback to computer vision heuristics
    is_leaf_cv = _check_leaf_with_cv(image_bytes)
    logger.info(f"CV validation result: {is_leaf_cv}")
    return is_leaf_cv


def predict_disease_from_image(image_bytes: bytes, mime: str = 'image/jpeg') -> dict:
    """
    Run disease prediction. Priority: Gemini Vision → TensorFlow model → heuristic.
    """
    if not image_bytes:
        raise DiseaseServiceError('Empty image', status=400)
    if len(image_bytes) > 8 * 1024 * 1024:
        raise DiseaseServiceError('Image too large (max 8MB)', status=400)

    # Validate image contains a crop/plant leaf before proceeding to classification
    if not _validate_image_is_leaf(image_bytes, mime):
        logger.info("Validation failed")
        raise DiseaseServiceError("No plant material detected", status=400)

    logger.info("Validation passed")
    logger.info("Prediction started")

    if _gemini_key():
        try:
            return _predict_gemini(image_bytes, mime)
        except DiseaseServiceError:
            pass

    try:
        return _predict_tensorflow(image_bytes)
    except DiseaseServiceError:
        pass

    return _predict_heuristic(image_bytes)
