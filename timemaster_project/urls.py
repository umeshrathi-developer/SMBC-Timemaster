"""
URL configuration for timemaster_project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.urls import re_path
from django.views.generic import RedirectView
from django.views.static import serve

urlpatterns = [
    path('', RedirectView.as_view(url='timesheet/', permanent=False)),
    path('login/', RedirectView.as_view(url='/timesheet/login/', permanent=False)),
    path('admin/', admin.site.urls),
    path('timesheet/', include('timesheet.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
elif settings.SERVE_MEDIA:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]

# Admin site customization
admin.site.site_header = "TimeMaster Administration"
admin.site.site_title = "TimeMaster Admin"
admin.site.index_title = "Welcome to TimeMaster Admin"
