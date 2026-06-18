from django.apps import AppConfig


class AgroConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'agro'

    def ready(self):
        # Schemes DB seed runs on first /schemes/ or /api/schemes request (see views.schemes_page)
        pass
