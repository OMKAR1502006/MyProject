import os
import requests
from typing import Dict, Any, List
from django.conf import settings

def calculate_yield_and_profit(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculates expected yield, revenue, expenses, profit, and margin %
    using baseline constants adjusted by multipliers.
    """
    crop_type = inputs.get('crop_type', 'Wheat').strip()
    try:
        farm_size = float(inputs.get('farm_size', 1))
    except (ValueError, TypeError):
        farm_size = 1.0

    soil_type = inputs.get('soil_type', 'loamy').strip().lower()
    season = inputs.get('season', 'winter').strip().lower()

    try:
        rainfall = float(inputs.get('rainfall', 500))
    except (ValueError, TypeError):
        rainfall = 500.0

    try:
        temperature = float(inputs.get('temperature', 25))
    except (ValueError, TypeError):
        temperature = 25.0

    try:
        seed_cost = float(inputs.get('seed_cost', 0))
    except (ValueError, TypeError):
        seed_cost = 0.0

    try:
        fertilizer_cost = float(inputs.get('fertilizer_cost', 0))
    except (ValueError, TypeError):
        fertilizer_cost = 0.0

    try:
        labor_cost = float(inputs.get('labor_cost', 0))
    except (ValueError, TypeError):
        labor_cost = 0.0

    # Base yield per acre in tonnes
    base_yields = {
        'rice': 2.2,
        'wheat': 1.8,
        'cotton': 1.1,
        'sugarcane': 38.0,
        'maize': 2.6,
        'soybean': 1.0,
        'onion': 9.5,
        'tomato': 13.0,
        'default': 1.5
    }

    # Market price per tonne in INR (estimated average rates)
    base_price_per_tonne = {
        'rice': 21830.0,      # ₹2,183 / quintal
        'wheat': 22750.0,     # ₹2,275 / quintal
        'cotton': 70000.0,
        'sugarcane': 3150.0,
        'maize': 20900.0,
        'soybean': 46000.0,
        'onion': 18000.0,
        'tomato': 25000.0,
        'default': 20000.0
    }

    crop_key = crop_type.lower()
    base_yield = base_yields.get(crop_key, base_yields['default'])
    price_per_tonne = base_price_per_tonne.get(crop_key, base_price_per_tonne['default'])

    # 1. Soil multiplier
    soil_multipliers = {
        'loamy': 1.0,
        'clayey': 0.95,
        'sandy': 0.75,
        'black': 1.08,
        'red': 0.9,
    }
    soil_mult = soil_multipliers.get(soil_type, 1.0)

    # 2. Season multiplier
    season_multipliers = {
        'wheat': {'winter': 1.0, 'monsoon': 0.3, 'summer': 0.2},
        'rice': {'monsoon': 1.0, 'winter': 0.6, 'summer': 0.5},
        'cotton': {'monsoon': 1.0, 'summer': 0.8, 'winter': 0.4},
        'sugarcane': {'monsoon': 1.0, 'winter': 0.9, 'summer': 0.8},
        'maize': {'monsoon': 1.0, 'winter': 0.85, 'summer': 0.75},
        'soybean': {'monsoon': 1.0, 'winter': 0.4, 'summer': 0.3},
        'onion': {'winter': 1.0, 'summer': 0.85, 'monsoon': 0.75},
        'tomato': {'winter': 1.0, 'summer': 0.9, 'monsoon': 0.8},
    }
    crop_season_mults = season_multipliers.get(crop_key, {'monsoon': 1.0, 'winter': 1.0, 'summer': 1.0})
    season_mult = crop_season_mults.get(season, 0.8)

    # 3. Weather multiplier - Temperature
    temp_mult = 1.0
    if crop_key == 'wheat' and temperature > 28:
        temp_mult -= 0.05 * (temperature - 28)
    elif crop_key == 'rice' and temperature < 22:
        temp_mult -= 0.04 * (22 - temperature)
    elif temperature > 40:
        temp_mult -= 0.1 * (temperature - 40)
    temp_mult = max(0.4, min(1.2, temp_mult))

    # 4. Weather multiplier - Rainfall
    rain_mult = 1.0
    if crop_key == 'rice' and rainfall < 600:
        rain_mult -= 0.0008 * (600 - rainfall)
    elif crop_key == 'wheat' and rainfall > 700:
        rain_mult -= 0.0005 * (rainfall - 700)
    elif rainfall < 200:
        rain_mult -= 0.3
    rain_mult = max(0.4, min(1.2, rain_mult))

    # Computations
    expected_yield = farm_size * base_yield * soil_mult * season_mult * temp_mult * rain_mult
    expected_yield = round(expected_yield, 2)

    estimated_expenses = seed_cost + fertilizer_cost + labor_cost
    estimated_revenue = round(expected_yield * price_per_tonne, 2)
    estimated_profit = round(estimated_revenue - estimated_expenses, 2)

    profit_margin = 0.0
    if estimated_revenue > 0:
        profit_margin = round((estimated_profit / estimated_revenue) * 100, 2)

    return {
        'expected_yield': expected_yield,
        'estimated_revenue': estimated_revenue,
        'estimated_expenses': estimated_expenses,
        'estimated_profit': estimated_profit,
        'profit_margin': profit_margin,
    }


def get_prediction_recommendations(inputs: Dict[str, Any], outputs: Dict[str, Any]) -> List[str]:
    """
    Generate agronomic advisory recommendations using LLM if available,
    otherwise falling back to structured rule-based instructions.
    """
    gemini_key = os.getenv('GEMINI_API_KEY') or getattr(settings, 'GEMINI_API_KEY', None)
    openai_key = os.getenv('OPENAI_API_KEY') or getattr(settings, 'OPENAI_API_KEY', None)

    crop = inputs.get('crop_type', 'Wheat')
    soil = inputs.get('soil_type', 'loamy')
    season = inputs.get('season', 'winter')
    rainfall = inputs.get('rainfall', 500)
    temp = inputs.get('temperature', 25)
    margin = outputs.get('profit_margin', 0)

    prompt = (
        "You are an expert Indian agronomist. Provide exactly 4 concise, bulleted recommendations "
        "for a farmer with the following profile. Keep responses under 60 words per recommendation.\n"
        f"Crop: {crop}, Soil: {soil}, Season: {season}, Rainfall: {rainfall}mm, Temp: {temp}C.\n"
        f"Predicted Profit Margin: {margin}%.\n"
        "Generate suggestions specifically in these categories:\n"
        "1. Yield improvement tips\n"
        "2. Irrigation advice\n"
        "3. Fertilizer recommendations\n"
        "4. Cost optimization suggestions\n"
        "Provide your response as a numbered list of 4 paragraphs without formatting markdown labels."
    )

    if gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            r = requests.post(url, json=payload, timeout=6)
            if r.status_code == 200:
                text = r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                if len(lines) >= 4:
                    return lines[:4]
        except Exception:
            pass

    if openai_key:
        try:
            headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
            payload = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 300
            }
            r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=6)
            if r.status_code == 200:
                text = r.json()['choices'][0]['message']['content'].strip()
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                if len(lines) >= 4:
                    return lines[:4]
        except Exception:
            pass

    # Static Fallback Rules
    recommendations = []
    # 1. Yield Tip
    recommendations.append(
        f"For better {crop} yield in {soil} soil, ensure crop rotation with legumes to restore nitrogen levels naturally and use high-yielding certified seeds."
    )
    # 2. Irrigation Advice
    if float(rainfall) < 400 or crop.lower() == 'rice':
        recommendations.append(
            "Adopt drip irrigation or sprinkler systems to conserve water and maintain optimal soil moisture without logging the root zone."
        )
    else:
        recommendations.append(
            "Schedule irrigation based on weather forecasts. Avoid watering before expected showers to prevent soil erosion and nutrient leaching."
        )
    # 3. Fertilizer recommendations
    recommendations.append(
        "Apply balanced NPK chemical fertilizers split into 2-3 doses matching growth stages, supplemented with well-rotted organic manure."
    )
    # 4. Cost Optimization
    recommendations.append(
        "Reduce labor costs by engaging in cooperative farming machinery sharing. Purchase bulk inputs directly from licensed government centers."
    )
    
    return recommendations
