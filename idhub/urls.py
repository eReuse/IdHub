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
from .admin import views as views_admin
from .user import views as views_user

app_name = 'idhub'

urlpatterns = [
    path("", RedirectView.as_view(url=reverse_lazy('idhub:login'),
        permanent=False)),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

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

    # Admin
    path('admin/dashboard/', views_admin.AdminDashboardView.as_view(),
        name='admin_dashboard'),
    path('admin/people/', views_admin.AdminPeopleListView.as_view(),
        name='admin_people_list'),
    path('admin/people/<int:pk>', views_admin.AdminPeopleView.as_view(),
        name='admin_people'),
    path('admin/people/<int:pk>/edit', views_admin.AdminPeopleEditView.as_view(),
        name='admin_people_edit'),
    path('admin/people/<int:pk>/del', views_admin.AdminPeopleDeleteView.as_view(),
        name='admin_people_delete'),
    path('admin/people/<int:pk>/activate', views_admin.AdminPeopleActivateView.as_view(),
        name='admin_people_activate'),
    path('admin/people/new/', views_admin.AdminPeopleRegisterView.as_view(),
        name='admin_people_new'),
    path('admin/roles/', views_admin.AdminRolesView.as_view(),
        name='admin_roles'),
    path('admin/services/', views_admin.AdminServicesView.as_view(),
        name='admin_services'),
    path('admin/credentials/', views_admin.AdminCredentialsView.as_view(),
        name='admin_credentials'),
    path('admin/credentials/new/', views_admin.AdminIssueCredentialsView.as_view(),
        name='admin_credentials_new'),
    path('admin/credentials/revoke/', views_admin.AdminRevokeCredentialsView.as_view(),
        name='admin_credentials_revoke'),
    path('admin/wallet/identities/', views_admin.AdminWalletIdentitiesView.as_view(),
        name='admin_wallet_identities'),
    path('admin/wallet/credentials/', views_admin.AdminWalletCredentialsView.as_view(),
        name='admin_wallet_credentials'),
    path('admin/wallet/config/issue/', views_admin.AdminWalletConfigIssuesView.as_view(),
        name='admin_wallet_config_issue'),
    path('admin/wallet/config/issue/', views_admin.AdminWalletConfigIssuesView.as_view(),
        name='admin_wallet_config_issue'),
    path('admin/schemes/', views_admin.AdminSchemesView.as_view(),
        name='admin_schemes'),
    path('admin/schemes/import', views_admin.AdminSchemesImportView.as_view(),
        name='admin_schemes_import'),
    path('admin/schemes/export/', views_admin.AdminSchemesExportView.as_view(),
        name='admin_schemes_export'),
    path('admin/import', views_admin.AdminImportView.as_view(),
        name='admin_import'),
    path('admin/export/', views_admin.AdminExportView.as_view(),
        name='admin_export'),
]
