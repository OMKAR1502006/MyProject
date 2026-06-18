"""
Client-side UI strings for weather.js, market.js, chatbot.js, and dynamic pages.
"""

LANGS = ('en', 'hi', 'mr', 'te', 'kn')

# Each key: en text + translations hi, mr, te, kn
_RAW = {
    'loading_weather': {
        'en': 'Fetching live weather data…',
        'hi': 'लाइव मौसम डेटा लोड हो रहा है…',
        'mr': 'थेट हवामान माहिती लोड होत आहे…',
        'te': 'లైవ్ వాతావరణ డేటా లోడ్ అవుతోంది…',
        'kn': 'ಲೈವ್ ಹವಾಮಾನ ಡೇಟಾ ಲೋಡ್ ಆಗುತ್ತಿದೆ…',
    },
    'loading_market': {
        'en': 'Loading mandi prices…',
        'hi': 'मंडी भाव लोड हो रहे हैं…',
        'mr': 'मंडी भाव लोड होत आहेत…',
        'te': 'మండి ధరలు లోడ్ అవుతున్నాయి…',
        'kn': 'ಮಂಡಿ ಬೆಲೆಗಳು ಲೋಡ್ ಆಗುತ್ತಿದೆ…',
    },
    'loading_schemes': {
        'en': 'Loading government schemes…',
        'hi': 'सरकारी योजनाएँ लोड हो रही हैं…',
        'mr': 'शासकीय योजना लोड होत आहेत…',
        'te': 'ప్రభుత్వ పథకాలు లోడ్ అవుతున్నాయి…',
        'kn': 'ಸರ್ಕಾರಿ ಯೋಜನೆಗಳು ಲೋಡ್ ಆಗುತ್ತಿದೆ…',
    },
    'loading_advisory': {
        'en': 'Getting crop recommendations…',
        'hi': 'फसल सिफारिशें लोड हो रही हैं…',
        'mr': 'पीक शिफारसी लोड होत आहेत…',
        'te': 'పంట సిఫార్సులు లోడ్ అవుతున్నాయి…',
        'kn': 'ಬೆಳೆ ಶಿಫಾರಸುಗಳು ಲೋಡ್ ಆಗುತ್ತಿದೆ…',
    },
    'analyzing_soil': {
        'en': 'Analyzing soil…',
        'hi': 'मिट्टी का विश्लेषण…',
        'mr': 'माती विश्लेषण…',
        'te': 'నేల విశ్లేషణ…',
        'kn': 'ಮಣ್ಣಿನ ವಿಶ್ಲೇಷಣೆ…',
    },
    'geo_denied': {
        'en': 'Allow location access or enter a city name.',
        'hi': 'स्थान की अनुमति दें या शहर का नाम लिखें।',
        'mr': 'स्थान परवानगी द्या किंवा शहराचे नाव टाका.',
        'te': 'లోకేషన్ అనుమతించండి లేదా నగరం పేరు నమోదు చేయండి.',
        'kn': 'ಸ್ಥಳ ಅನುಮತಿಸಿ ಅಥವಾ ನಗರದ ಹೆಸರು ನಮೂದಿಸಿ.',
    },
    'fetch_failed': {
        'en': 'Failed to fetch data',
        'hi': 'डेटा लोड नहीं हो सका',
        'mr': 'माहिती मिळाली नाही',
        'te': 'డేటా లోడ్ కాలేదు',
        'kn': 'ಡೇಟಾ ಲೋಡ್ ಆಗಲಿಲ್ಲ',
    },
    'no_alerts': {
        'en': 'No major weather alerts for the next 5 days.',
        'hi': 'अगले 5 दिनों में कोई बड़ी मौसम चेतावनी नहीं।',
        'mr': 'पुढील 5 दिवसांत मोठी हवामान सूचना नाही.',
        'te': 'తదుపరి 5 రోజుల్లో పెద్ద వాతావరణ హెచ్చరికలు లేవు.',
        'kn': 'ಮುಂದಿನ 5 ದಿನಗಳಲ್ಲಿ ದೊಡ್ಡ ಹವಾಮಾನ ಎಚ್ಚರಿಕೆ ಇಲ್ಲ.',
    },
    'no_market_results': {
        'en': 'No mandi prices found. Try another crop or state.',
        'hi': 'कोई मंडी भाव नहीं मिला। दूसी फसल या राज्य आज़माएँ।',
        'mr': 'मंडी भाव सापडले नाहीत. दुसरी पिक किंवा राज्य निवडा.',
        'te': 'మండి ధరలు కనిపించలేదు. వేరే పంట లేదా రాష్ట్రం ప్రయత్నించండి.',
        'kn': 'ಮಂಡಿ ಬೆಲೆಗಳು ಕಂಡುಬಂದಿಲ್ಲ. ಬೇರೆ ಬೆಳೆ ಅಥವಾ ರಾಜ್ಯ ಪ್ರಯತ್ನಿಸಿ.',
    },
    'best_market': {
        'en': 'Best market to sell',
        'hi': 'बेचने के लिए सबसे अच्छी मंडी',
        'mr': 'विक्रीसाठी सर्वोत्तम मंडी',
        'te': 'అమ్మకానికి ఉత్తమ మండి',
        'kn': 'ಮಾರಾಟಕ್ಕೆ ಉತ್ತಮ ಮಂಡಿ',
    },
    'price_trend': {
        'en': 'Price trend',
        'hi': 'भाव का रुझान',
        'mr': 'भावाचा कल',
        'te': 'ధరల ధోరణి',
        'kn': 'ಬೆಲೆ ಪ್ರವೃತ್ತಿ',
    },
    'recommendation': {
        'en': 'Recommendation',
        'hi': 'सलाह',
        'mr': 'शिफारस',
        'te': 'సూచన',
        'kn': 'ಶಿಫಾರಸು',
    },
    'search': {
        'en': 'Search',
        'hi': 'खोजें',
        'mr': 'शोध',
        'te': 'వెతకండి',
        'kn': 'ಹುಡುಕಿ',
    },
    'image_question': {
        'en': '[Photo question]',
        'hi': '[फोटो प्रश्न]',
        'mr': '[फोटो प्रश्न]',
        'te': '[ఫోటో ప్రశ్న]',
        'kn': '[ಫೋಟೋ ಪ್ರಶ್ನೆ]',
    },
    'ask_again_placeholder': {
        'en': 'Ask your next question…',
        'hi': 'अगला प्रश्न पूछें…',
        'mr': 'पुढचा प्रश्न विचारा…',
        'te': 'తదుపరి ప్రశ్న అడగండి…',
        'kn': 'ಮುಂದಿನ ಪ್ರಶ್ನೆ ಕೇಳಿ…',
    },
    'chat_thinking': {
        'en': 'AgroSathi is thinking…',
        'hi': 'AgroSathi सोच रहा है…',
        'mr': 'AgroSathi विचार करत आहे…',
        'te': 'AgroSathi ఆలోచిస్తోంది…',
        'kn': 'AgroSathi ಯೋಚಿಸುತ್ತಿದೆ…',
    },
    'no_schemes': {
        'en': 'No schemes found. Try another state or category.',
        'hi': 'कोई योजना नहीं मिली।',
        'mr': 'योजना सापडली नाही.',
        'te': 'పథకాలు కనిపించలేదు.',
        'kn': 'ಯೋಜನೆಗಳು ಕಂಡುಬಂದಿಲ್ಲ.',
    },
    'failed_schemes': {
        'en': 'Failed to load schemes.',
        'hi': 'योजनाएँ लोड नहीं हो सकीं।',
        'mr': 'योजना लोड झाल्या नाहीत.',
        'te': 'పథకాలు లోడ్ కాలేదు.',
        'kn': 'ಯೋಜನೆಗಳನ್ನು ಲೋಡ್ ಮಾಡಲಾಗಲಿಲ್ಲ.',
    },
    'official_portal': {
        'en': 'Official portal',
        'hi': 'आधिकारिक पोर्टल',
        'mr': 'अधिकृत पोर्टल',
        'te': 'అధికారిక పోర్టల్',
        'kn': 'ಅಧಿಕೃತ ಪೋರ್ಟಲ್',
    },
    'recommended_crops': {
        'en': 'Recommended crops',
        'hi': 'अनुशंसित फसलें',
        'mr': 'शिफारस केलेली पिके',
        'te': 'సిఫార్సు చేసిన పంటలు',
        'kn': 'ಶಿಫಾರಸು ಮಾಡಿದ ಬೆಳೆಗಳು',
    },
    'analysis_failed': {
        'en': 'Analysis failed',
        'hi': 'विश्लेषण विफल',
        'mr': 'विश्लेषण अयशस्वी',
        'te': 'విశ్లేషణ విఫలమైంది',
        'kn': 'ವಿಶ್ಲೇಷಣೆ ವಿಫಲವಾಯಿತು',
    },
    'eligibility': {
        'en': 'Eligibility',
        'hi': 'पात्रता',
        'mr': 'पात्रता',
        'te': 'అర్హత',
        'kn': 'ಅರ್ಹತೆ',
    },
    'benefits': {
        'en': 'Benefits',
        'hi': 'लाभ',
        'mr': 'फायदे',
        'te': 'ప్రయోజనాలు',
        'kn': 'ಪ್ರಯೋಜನಗಳು',
    },
    'forecast_unavailable': {
        'en': 'Forecast unavailable',
        'hi': 'पूर्वानुमान उपलब्ध नहीं',
        'mr': 'अंदाज उपलब्ध नाही',
        'te': 'సూచన అందుబాటులో లేదు',
        'kn': 'ಮುನ್ಸೂಚನೆ ಲಭ್ಯವಿಲ್ಲ',
    },
}

JS_STRINGS = _RAW


def get_js_translations() -> dict:
    out = {lang: {} for lang in LANGS}
    for key, translations in JS_STRINGS.items():
        for lang in LANGS:
            out[lang][key] = translations.get(lang, translations.get('en', key))
    return out


def js_t(key: str, lang: str) -> str:
    lang = (lang or 'en').split('-')[0]
    entry = JS_STRINGS.get(key, {})
    return entry.get(lang) or entry.get('en', key)
