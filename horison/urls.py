from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path("admin/", admin.site.urls),

    path("auth/", include("authentication.urls")),

    path("geoportail/", include("geoportail.urls")),
    path("agriculture/", include("agriculture.urls")),
    path("api/cartotheque/", include("cartotheque.api_urls")),
]


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )

    urlpatterns += static(
        settings.STATIC_URL,
        document_root=settings.STATIC_ROOT
    )
