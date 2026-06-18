"""Root URL configuration for AgroSathi."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('agro.urls')),
]

if settings.DEBUG:
    # Serve uploaded disease/chat images
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Serve live files from agro/static (not stale staticfiles/ copy)
    urlpatterns += staticfiles_urlpatterns()
