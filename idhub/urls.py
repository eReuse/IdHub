"""
URL configuration for trustchain_idhub project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
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
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from django.urls import path, reverse_lazy
from .views import LoginView
from .admin.views import AdminDashboardView
from .user import views as views_user


app_name = 'idhub'

urlpatterns = [
    path("", RedirectView.as_view(url=reverse_lazy('idhub:login'),
        permanent=False)),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('admin/dashboard/', AdminDashboardView.as_view(),
        name='admin_dashboard'),

    # User
    path('user/dashboard/', views_user.UserDashboardView.as_view(),
        name='user_dashboard'),
    path('user/profile/', views_user.UserProfileView.as_view(),
        name='user_profile'),
    path('user/roles/', views_user.UserRolesView.as_view(),
        name='user_roles'),
    path('user/gdpr/', views_user.UserGDPRView.as_view(),
        name='user_gdpr'),
    path('user/identities/', views_user.UserIdentitiesView.as_view(),
        name='user_identities'),
    path('user/credentials/', views_user.UserCredentialsView.as_view(),
        name='user_credentials'),
    path('user/credentials_required/',
        views_user.UserCredentialsRequiredView.as_view(),
        name='user_credentials_required'),
    path('user/credentials_presentation/',
        views_user.UserCredentialsPresentationView.as_view(),
        name='user_credentials_presentation'),
]
