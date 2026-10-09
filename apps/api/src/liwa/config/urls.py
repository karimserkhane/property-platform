from django.conf import settings
from django.contrib import admin
from django.urls import path

from liwa.api.router import api

urlpatterns = [path("api/v1/", api.urls)]

# Staff access will be designed and tested before enabling this outside local development.
if settings.DEBUG:
    urlpatterns.append(path("admin/", admin.site.urls))
