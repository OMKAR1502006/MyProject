from datetime import timedelta
from django.utils import timezone
from agro.models import VoiceCache

def get_cached_voice(text: str, language: str) -> bytes:
    """
    Looks up a cached voice clip in the database.
    Prunes expired records (older than 24 hours).
    """
    limit_time = timezone.now() - timedelta(days=1)
    VoiceCache.objects.filter(created_at__lt=limit_time).delete()

    record = VoiceCache.objects.filter(response_text=text, language=language).first()
    if record:
        return record.generated_audio
    return None

def set_cached_voice(text: str, language: str, audio_bytes: bytes):
    """
    Saves a generated voice clip to the cache.
    Prunes expired records (older than 24 hours).
    """
    limit_time = timezone.now() - timedelta(days=1)
    VoiceCache.objects.filter(created_at__lt=limit_time).delete()

    if audio_bytes:
        VoiceCache.objects.create(
            response_text=text,
            language=language,
            generated_audio=audio_bytes
        )
