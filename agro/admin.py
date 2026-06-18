from django.contrib import admin

from .models import (
    ChatHistory,
    CropHistory,
    CropWatchlist,
    DiseaseReport,
    FarmerProfile,
    GovernmentScheme,
    MarketSearchHistory,
)


@admin.register(FarmerProfile)
class FarmerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'district', 'state', 'primary_crop', 'phone')
    search_fields = ('user__username', 'district', 'village', 'phone')


@admin.register(CropHistory)
class CropHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'crop', 'soil_type', 'season', 'probability', 'created_at')
    list_filter = ('season', 'soil_type')
    search_fields = ('user__username', 'crop')


@admin.register(DiseaseReport)
class DiseaseReportAdmin(admin.ModelAdmin):
    list_display = ('user', 'disease', 'confidence', 'created_at')
    list_filter = ('disease',)
    search_fields = ('user__username', 'disease')


@admin.register(MarketSearchHistory)
class MarketSearchHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'crop', 'state', 'district', 'results_count', 'created_at')
    search_fields = ('user__username', 'crop', 'state')


@admin.register(CropWatchlist)
class CropWatchlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'crop', 'state', 'created_at')
    search_fields = ('user__username', 'crop')


@admin.register(GovernmentScheme)
class GovernmentSchemeAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'scheme_id', 'is_active', 'last_updated')
    list_filter = ('category', 'is_active')
    search_fields = ('title', 'scheme_id', 'description')


@admin.register(ChatHistory)
class ChatHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'language', 'provider', 'created_at')
    search_fields = ('user__username', 'question', 'answer')
    readonly_fields = ('created_at',)
