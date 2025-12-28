from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="Incident Management API",
        default_version='v1',
        description="API for managing incidents",
        terms_of_service="https://www.example.com/terms/",
        contact=openapi.Contact(email="contact@example.com"),
        license=openapi.License(name="Your License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Frontend pages
    path('', TemplateView.as_view(template_name='dashboard.html'), name='dashboard'),
    path('trigger/', TemplateView.as_view(template_name='trigger.html'), name='trigger'),
    path('oncall/', TemplateView.as_view(template_name='oncall.html'), name='oncall'),
    path('metrics/', TemplateView.as_view(template_name='metrics.html'), name='metrics'),
    
    # API endpoints
    path('api/', include('incidents.urls')),
    
    # Swagger API docs
    path('api/schema/swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/schema/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
