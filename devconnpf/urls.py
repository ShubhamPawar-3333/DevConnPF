"""
URL configuration for devconnpf project.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('social_django.urls', namespace='social')),
    path('api/', include('explorer.urls')),
    path('api/profiles/', include('profiles.urls')),
]
