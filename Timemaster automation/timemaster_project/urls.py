"""
URL configuration for timemaster_project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(url='accounts/login/', permanent=False)),
    path('login/', RedirectView.as_view(url='timesheet/login/', permanent=False)),
    path('admin/', admin.site.urls),
    path('timesheet/', include('timesheet.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/', RedirectView.as_view(url='login/', permanent=False)), 
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Admin site customization
admin.site.site_header = "TimeMaster Administration"
admin.site.site_title = "TimeMaster Admin"
admin.site.index_title = "Welcome to TimeMaster Admin"
