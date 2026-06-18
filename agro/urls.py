from django.urls import path

from . import views

urlpatterns = [
    # Public
    path('', views.home, name='home'),
    path('api/public/preview/', views.public_preview, name='public_preview'),
    path('i18n/set-language/', views.set_language, name='set_language'),

    # Authentication
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),

    # Protected pages
    path('dashboard/', views.dashboard, name='dashboard'),
    path('smart/', views.smart_advisory, name='smart_advisory'),
    path('disease/', views.disease_detection_page, name='disease_detection_page'),
    path('soil/', views.soil_analysis_page, name='soil_analysis_page'),
    path('weather/', views.weather_page, name='weather_page'),
    path('market/', views.market_page, name='market_page'),
    path('chatbot/', views.chatbot_page, name='chatbot_page'),
    path('schemes/', views.schemes_page, name='schemes_page'),

    # API (trailing slashes — avoids POST redirect issues)
    path('api/schemes/', views.schemes, name='schemes'),
    path('api/schemes', views.schemes),
    path('api/crop-advisory/', views.crop_advisory, name='crop_advisory'),
    path('api/crop-advisory', views.crop_advisory),
    path('api/detect-disease/', views.detect_disease, name='detect_disease'),
    path('api/detect-disease', views.detect_disease),
    path('api/soil-analysis/', views.soil_analysis, name='soil_analysis'),
    path('api/soil-analysis', views.soil_analysis),
    path('api/weather/', views.weather_api, name='weather_api'),
    path('api/market-prices/', views.market_prices_api, name='market_prices_api'),
    path('api/market-prices', views.market_prices_api),
    path('api/market-prices/export/', views.market_export_csv, name='market_export_csv'),
    path('api/market-watchlist/', views.market_watchlist_api, name='market_watchlist_api'),
    path('api/chat/', views.chat_api, name='chat_api'),
    path('api/chatbot/', views.chatbot_api, name='chatbot_api'),
    path('api/chatbot', views.chatbot_api),
    path('api/chat/history/', views.chat_history_api, name='chat_history_api'),
    path('api/tts/', views.tts_api, name='tts_api'),
    path('yield/', views.yield_prediction_page, name='yield_prediction_page'),
    path('api/yield-prediction/', views.api_yield_prediction, name='api_yield_prediction'),
    path('schemes/eligibility/', views.scheme_eligibility_page, name='scheme_eligibility_page'),
    path('api/schemes/eligibility/', views.api_scheme_eligibility, name='api_scheme_eligibility'),
    path('api/schemes/favorite/', views.toggle_favorite_scheme, name='toggle_favorite_scheme'),
    path('api/status/', views.api_status, name='api_status'),
]
