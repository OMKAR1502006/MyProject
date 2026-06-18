# AgroSathiDjango: AI-Powered Smart Farming Assistant

## Overview

AgroSathiDjango is a Django-based smart farming platform built to support farmers with practical, data-driven decision tools. It combines AI, machine learning, live APIs, and local fallback layers to deliver weather forecasting, mandi price tracking, crop health analysis, soil guidance, chatbot assistance, and government scheme discovery.

The platform is farmer-centric and designed to stay functional even when external APIs are unavailable.

## Features

- **Weather forecasting**
  - Primary provider: OpenWeatherMap
  - Fallback provider: Open-Meteo
  - Includes farm-friendly alerts and localized weather guidance

- **Market mandi price tracking**
  - Live Agmarknet integration via data.gov.in
  - Cached or sample fallback when live pricing is unavailable
  - Search by crop, state, district, and market
  - Export CSV support for offline analysis

- **AI Chatbot**
  - Primary AI: Google Gemini
  - Optional fallback: OpenAI
  - Rule-based fallback keeps chat working without API keys
  - Supports multilingual farmer conversations

- **Plant disease detection**
  - Primary detection: Gemini Vision image analysis
  - Secondary option: local TensorFlow model inference
  - Heuristic fallback using image color features and rules

- **Soil analysis and crop recommendation**
  - Evaluates NPK, pH, soil type, crop type, and rainfall
  - Generates fertilizer suggestions and soil health classification
  - Recommends crops based on season and soil conditions

- **Government schemes discovery**
  - Browse local scheme catalog
  - Search by category, state, and eligibility
  - Save favorite schemes for later reference

- **Voice / TTS support**
  - Converts chatbot replies to speech
  - Caches generated audio for faster replay

- **Multilingual support**
  - Kannada, Hindi, Marathi, Telugu, English
  - Language preferences persist in user sessions and profiles

- **Offline resilience**
  - Local rule-based fallbacks keep the app usable without full API access
  - Cached data preserves core functionality in low-connectivity environments

## Architecture

AgroSathiDjango follows Django MVC architecture with a modular service layer.

- `views.py` handles HTTP requests and returns rendered pages or JSON output.
- Service modules encapsulate business logic and external integrations.
- Database models persist farmer profiles, history, reports, and cache data.

### Request flow

1. User opens the dashboard or feature page.
2. Django routes the request via `urls.py`.
3. A view in `agro/views.py` processes the request.
4. The view calls the corresponding service module.
5. The service interacts with APIs or fallback logic.
6. Results are returned to the view.
7. The UI renders the final output.
8. AI-enhanced responses are used when available.

### Core services

- `weather.py` — weather data, geocoding, forecast aggregation, alerts
- `market.py` — mandi pricing, Agmarknet integration, caching, market insights
- `chatbot.py` — AI prompt generation, provider selection, multilingual responses
- `disease.py` — plant disease prediction using image analysis and fallbacks
- `tts.py` — text-to-speech generation and voice caching

## Project Structure

```
AgroSathiDjango/
├── manage.py
├── README.md
├── requirements.txt
├── requirements-ml.txt
├── AgroSathiDjango/
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── ...
└── agro/
    ├── views.py
    ├── models.py
    ├── urls.py
    ├── services/
    │   ├── weather.py
    │   ├── market.py
    │   ├── chatbot.py
    │   ├── disease.py
    │   ├── tts.py
    │   └── ...
    ├── templates/
    ├── static/
    ├── data/
    └── ml/
```

## How It Works

1. User opens the platform and navigates to a feature page.
2. Django routes the request through `agro/urls.py`.
3. The matching view in `agro/views.py` receives the request.
4. The view forwards the request to the appropriate service layer.
5. The service attempts to call the configured external API.
6. If the primary API fails, the service uses a secondary API or local fallback.
7. The service returns structured results to the view.
8. The view returns HTML or JSON to the browser.
9. The UI displays weather, mandi prices, AI chat responses, disease diagnosis, or soil advice.
10. If AI services are available, answers are enriched with Gemini/OpenAI context.

## API Integrations

- **OpenWeatherMap** — primary weather API
- **Open-Meteo** — fallback weather source with no API key required
- **Agmarknet** — live mandi price data via data.gov.in
- **Google Gemini** — primary AI chatbot and image analysis service
- **OpenAI** — optional chatbot fallback provider

## Fallback System

This project uses a three-level fallback strategy:

1. **Primary API** — use the main external service when configured.
2. **Secondary API** — switch to a backup service if the primary provider fails.
3. **Local fallback** — use rule-based logic or cached data when external APIs are unavailable.

Examples:
- Weather: `OpenWeatherMap → Open-Meteo`
- Market prices: `Agmarknet → cached sample data`
- Chat: `Gemini → OpenAI → rule-based fallback`
- Disease detection: `Gemini Vision → TensorFlow model → heuristic color analysis`

## Setup Instructions

```bash
python -m venv venv
# Windows
venv\\Scripts\\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

Configure environment variables:

```bash
copy .env.example .env
```

Edit `.env` and add your API keys:

- `GEMINI_API_KEY`
- `AGMARKNET_API_KEY`
- `OPENWEATHER_API_KEY`
- `OPENAI_API_KEY` (optional)

Run migrations and start the server:

```bash
python manage.py migrate
python manage.py runserver
```

Visit `http://127.0.0.1:8000/`.

## Tech Stack

- Django
- Python
- REST APIs
- Google Gemini / OpenAI
- TensorFlow (optional)
- HTML / CSS / JavaScript

## Future Improvements

- Mobile app support for farmers on the go
- Satellite and remote sensing data integration
- Advanced ML crop yield and pest prediction models
- WhatsApp alerts and notification system

---

AgroSathiDjango is built to deliver resilient, AI-enhanced farming support with a modern developer-friendly codebase.

contributor -pramod,omkar,prem