"""
URLs الرئيسية لخدمة الرسائل - منصة نائبك.كوم
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from rest_framework.documentation import include_docs_urls
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# إعداد Swagger/OpenAPI
schema_view = get_schema_view(
    openapi.Info(
        title="خدمة الرسائل - منصة نائبك.كوم",
        default_version='v1',
        description="واجهة برمجية لخدمة الرسائل والمحادثات بين المواطنين والنواب",
        terms_of_service="https://naebak.com/terms/",
        contact=openapi.Contact(email="info@naebak.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    # لوحة الإدارة
    path('admin/', admin.site.urls),
    
    # APIs الرئيسية
    path('', include('messages.urls')),
    
    # المصادقة والتوثيق
    path('api/auth/', include('rest_framework.urls')),
    
    # التوثيق التفاعلي
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('api/docs/', include_docs_urls(title='خدمة الرسائل API')),
    
    # Health check
    path('health/', lambda request: HttpResponse('OK')),
]

# إضافة ملفات الوسائط في وضع التطوير
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
