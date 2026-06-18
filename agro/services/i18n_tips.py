"""Localized farming tips and alert labels for API responses."""

from django.utils.translation import gettext as _

# Weather farming tips — keys matched in weather service
WEATHER_TIP_KEYS = {
    'irrigate_early': lambda: _(
        'Irrigate early morning or evening to reduce evaporation loss.'
    ),
    'delay_transplant': lambda: _(
        'Delay transplanting; use mulching to protect young plants from cold.'
    ),
    'high_humidity': lambda: _(
        'High humidity — avoid overhead irrigation; monitor for fungal diseases.'
    ),
    'heavy_rain': lambda: _(
        'Heavy rain expected — ensure field drainage and postpone pesticide spray.'
    ),
    'rain_harvest': lambda: _(
        'Rain likely in coming days — plan harvesting before wet spell if crops are ready.'
    ),
    'strong_wind': lambda: _(
        'Strong winds — avoid spraying; check greenhouse and trellis structures.'
    ),
    'dry_hot': lambda: _(
        'Dry and hot — increase irrigation frequency for fruiting crops.'
    ),
    'favourable': lambda: _(
        'Weather looks favourable — good time for routine field inspection and weeding.'
    ),
}

ALERT_LABELS = {
    'heat': lambda: _('Heat Alert'),
    'cold': lambda: _('Cold Alert'),
    'frost': lambda: _('Frost Alert'),
    'rain': lambda: _('Rain Alert'),
    'high_wind': lambda: _('High Wind'),
}

MARKET_LABELS = {
    'high_demand': lambda: _('High Demand'),
    'low_demand': lambda: _('Low Demand'),
    'stable': lambda: _('Stable'),
    'good_selling_time': lambda: _('Good Selling Time'),
}
