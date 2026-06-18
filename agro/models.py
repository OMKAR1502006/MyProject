from django.db import models
from django.contrib.auth.models import User


class FarmerProfile(models.Model):
    """Extended profile for registered farmers."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='farmer_profile')
    phone = models.CharField(max_length=15, blank=True)
    village = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    primary_crop = models.CharField(max_length=80, blank=True)
    farm_size_acres = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    preferred_language = models.CharField(
        max_length=10,
        default='en',
        choices=[
            ('en', 'English'),
            ('hi', 'Hindi'),
            ('mr', 'Marathi'),
            ('te', 'Telugu'),
            ('kn', 'Kannada'),
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.username} — {self.district or "Farmer"}'


class CropHistory(models.Model):
    """Stores crop advisory requests per farmer."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='crop_history')
    crop = models.CharField(max_length=80)
    soil_type = models.CharField(max_length=50, blank=True)
    season = models.CharField(max_length=30, blank=True)
    temperature = models.FloatField(null=True, blank=True)
    ph = models.FloatField(null=True, blank=True)
    rainfall = models.FloatField(null=True, blank=True)
    probability = models.FloatField(default=0.0)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Crop histories'

    def __str__(self):
        return f'{self.user.username}: {self.crop} ({self.probability:.0%})'


class DiseaseReport(models.Model):
    """Stores disease detection results per farmer."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='disease_reports')
    disease = models.CharField(max_length=120)
    confidence = models.FloatField(default=0.0)
    image = models.ImageField(upload_to='disease_reports/%Y/%m/', blank=True, null=True)
    treatment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username}: {self.disease} ({self.confidence:.0%})'


class MarketSearchHistory(models.Model):
    """Farmer mandi price search history."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='market_searches')
    crop = models.CharField(max_length=80, blank=True)
    state = models.CharField(max_length=80, blank=True)
    district = models.CharField(max_length=80, blank=True)
    market = models.CharField(max_length=120, blank=True)
    results_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Market search histories'

    def __str__(self):
        return f'{self.user.username}: {self.crop or "all"} @ {self.created_at:%Y-%m-%d}'


class CropWatchlist(models.Model):
    """Favorite crops for price monitoring."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='crop_watchlist')
    crop = models.CharField(max_length=80)
    state = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['crop']
        unique_together = [['user', 'crop', 'state']]

    def __str__(self):
        return f'{self.user.username} → {self.crop}'


class GovernmentScheme(models.Model):
    """Central and state government farmer welfare schemes."""

    scheme_id = models.CharField(max_length=80, unique=True)
    title = models.CharField(max_length=255)
    short_description = models.CharField(max_length=500, blank=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=60, default='general')
    states = models.JSONField(default=list, blank=True)
    eligibility = models.TextField(blank=True)
    benefits = models.TextField(blank=True)
    application_steps = models.JSONField(default=list, blank=True)
    apply_url = models.URLField(max_length=500, blank=True)
    last_updated = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title


class ChatHistory(models.Model):
    """Stores farmer ↔ AI chatbot conversations."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_history')
    question = models.TextField()
    answer = models.TextField()
    language = models.CharField(max_length=10, default='en')
    provider = models.CharField(max_length=20, blank=True, default='')
    image = models.ImageField(upload_to='chat_images/%Y/%m/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name_plural = 'Chat histories'

    def __str__(self):
        preview = (self.question[:50] + '…') if len(self.question) > 50 else self.question
        return f'{self.user.username}: {preview}'


class YieldPredictionHistory(models.Model):
    """Stores farmer yield & profit prediction inputs and outputs."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='yield_predictions')
    
    # Inputs
    crop_type = models.CharField(max_length=80)
    farm_size_acres = models.DecimalField(max_digits=8, decimal_places=2)
    soil_type = models.CharField(max_length=50)
    season = models.CharField(max_length=30)
    rainfall = models.FloatField()
    temperature = models.FloatField()
    seed_cost = models.DecimalField(max_digits=10, decimal_places=2)
    fertilizer_cost = models.DecimalField(max_digits=10, decimal_places=2)
    labor_cost = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Outputs
    expected_yield_tonnes = models.FloatField()
    estimated_revenue = models.DecimalField(max_digits=12, decimal_places=2)
    estimated_expenses = models.DecimalField(max_digits=12, decimal_places=2)
    estimated_profit = models.DecimalField(max_digits=12, decimal_places=2)
    profit_margin_percent = models.FloatField()
    
    # Recommendations (stored as JSON)
    recommendations = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Yield prediction histories'

    def __str__(self):
        return f'{self.user.username}: {self.crop_type} ({self.created_at:%Y-%m-%d})'


class FavoriteScheme(models.Model):
    """Stores user's favorite government schemes."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorite_schemes')
    scheme_id = models.CharField(max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['user', 'scheme_id']]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} ★ {self.scheme_id}'


class VoiceCache(models.Model):
    """Temporary server-side cache for generated Text-to-Speech audio clips."""

    response_text = models.TextField()
    language = models.CharField(max_length=10)
    generated_audio = models.BinaryField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['response_text', 'language']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.language}: {self.response_text[:30]}…'

