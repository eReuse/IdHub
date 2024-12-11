"""
URL configuration for dhub project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.urls import path, include

urlpatterns = [
    # path('api/', include('snapshot.urls')),
    path("", include("login.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("evidence/", include("evidence.urls")),
    path("device/", include("device.urls")),
    path("admin/", include("admin.urls")),
    path("user/", include("user.urls")),
    path("lot/", include("lot.urls")),
    path('api/', include('api.urls')),
]

if settings.DPP:
    urlpatterns.extend([
        path('dpp/', include('dpp.urls')),
        path('did/', include('did.urls')),
    ])
