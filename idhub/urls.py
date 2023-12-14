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
# from .verification_portal import views as views_verification_portal

app_name = 'idhub'

urlpatterns = [
    path("", RedirectView.as_view(url=reverse_lazy('idhub:login'),
        permanent=False)),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('auth/password_reset/', 
        auth_views.PasswordResetView.as_view(
            template_name='auth/password_reset.html',
            email_template_name='auth/password_reset_email.txt',
            html_email_template_name='auth/password_reset_email.html',
            subject_template_name='auth/password_reset_subject.txt',
            success_url=reverse_lazy('idhub:password_reset_done')
        ),
        name='password_reset'
    ),
    path('auth/password_reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='auth/password_reset_done.html'
        ),
        name='password_reset_done'
    ),
    path('auth/reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='auth/password_reset_confirm.html',
            success_url=reverse_lazy('idhub:password_reset_complete')
        ),
        name='password_reset_confirm'
    ),
    path('auth/reset/done/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='auth/password_reset_complete.html'
        ),
        name='password_reset_complete'
    ),

    # User
    path('user/dashboard/', views_user.DashboardView.as_view(),
        name='user_dashboard'),
    path('user/profile/', views_user.ProfileView.as_view(),
        name='user_profile'),
    path('user/roles/', views_user.RolesView.as_view(),
        name='user_roles'),
    path('user/gdpr/', views_user.GDPRView.as_view(),
        name='user_gdpr'),
    path('user/identities/', views_user.DidsView.as_view(),
        name='user_dids'),
    path('user/dids/new/', views_user.DidRegisterView.as_view(),
        name='user_dids_new'),
    path('user/dids/<int:pk>/', views_user.DidEditView.as_view(),
        name='user_dids_edit'),
    path('user/dids/<int:pk>/del/', views_user.DidDeleteView.as_view(),
        name='user_dids_del'),
    path('user/credentials/', views_user.CredentialsView.as_view(),
        name='user_credentials'),
    path('user/credentials/<int:pk>', views_user.CredentialView.as_view(),
        name='user_credential'),
    path('user/credentials/<int:pk>/json', views_user.CredentialJsonView.as_view(),
        name='user_credential_json'),
    path('user/credentials/request/',
        views_user.CredentialsRequestView.as_view(),
        name='user_credentials_request'),
    path('user/credentials_presentation/demand',
        views_user.DemandAuthorizationView.as_view(),
        name='user_demand_authorization'),

    # Admin
    path('admin/dashboard/', views_admin.DashboardView.as_view(),
        name='admin_dashboard'),
    path('admin/people/', views_admin.PeopleListView.as_view(),
        name='admin_people_list'),
    path('admin/people/<int:pk>', views_admin.PeopleView.as_view(),
        name='admin_people'),
    path('admin/people/<int:pk>/edit', views_admin.PeopleEditView.as_view(),
        name='admin_people_edit'),
    path('admin/people/<int:pk>/del', views_admin.PeopleDeleteView.as_view(),
        name='admin_people_delete'),
    path('admin/people/<int:pk>/activate', views_admin.PeopleActivateView.as_view(),
        name='admin_people_activate'),
    path('admin/people/new/', views_admin.PeopleRegisterView.as_view(),
        name='admin_people_new'),
    path('admin/people/<int:pk>/membership/new/', views_admin.PeopleMembershipRegisterView.as_view(),
        name='admin_people_membership_new'),
    path('admin/membership/<int:pk>/edit/', views_admin.PeopleMembershipEditView.as_view(),
        name='admin_people_membership_edit'),
    path('admin/membership/<int:pk>/del/', views_admin.PeopleMembershipDeleteView.as_view(),
        name='admin_people_membership_del'),
    path('admin/people/<int:pk>/rol/new/', views_admin.PeopleRolRegisterView.as_view(),
        name='admin_people_rol_new'),
    path('admin/people/<int:pk>/rol/edit/', views_admin.PeopleRolEditView.as_view(),
        name='admin_people_rol_edit'),
    path('admin/people/<int:pk>/rol/del/', views_admin.PeopleRolDeleteView.as_view(),
        name='admin_people_rol_del'),
    path('admin/roles/', views_admin.RolesView.as_view(),
        name='admin_roles'),
    path('admin/roles/new', views_admin.RolRegisterView.as_view(),
        name='admin_rol_new'),
    path('admin/roles/<int:pk>', views_admin.RolEditView.as_view(),
        name='admin_rol_edit'),
    path('admin/roles/<int:pk>/del', views_admin.RolDeleteView.as_view(),
        name='admin_rol_del'),
    path('admin/services/', views_admin.ServicesView.as_view(),
        name='admin_services'),
    path('admin/services/new', views_admin.ServiceRegisterView.as_view(),
        name='admin_service_new'),
    path('admin/services/<int:pk>', views_admin.ServiceEditView.as_view(),
        name='admin_service_edit'),
    path('admin/services/<int:pk>/del', views_admin.ServiceDeleteView.as_view(),
        name='admin_service_del'),
    path('admin/credentials/', views_admin.CredentialsView.as_view(),
        name='admin_credentials'),
    path('admin/credentials/<int:pk>/', views_admin.CredentialView.as_view(),
        name='admin_credential'),
    path('admin/credentials/<int:pk>/json', views_admin.CredentialJsonView.as_view(),
        name='admin_credential_json'),
    path('admin/credentials/<int:pk>/revoke/', views_admin.RevokeCredentialsView.as_view(),
        name='admin_credentials_revoke'),
    path('admin/credentials/<int:pk>/del/', views_admin.DeleteCredentialsView.as_view(),
        name='admin_credentials_delete'),
    path('admin/wallet/identities/', views_admin.DidsView.as_view(),
        name='admin_dids'),
    path('admin/dids/new/', views_admin.DidRegisterView.as_view(),
        name='admin_dids_new'),
    path('admin/dids/<int:pk>/', views_admin.DidEditView.as_view(),
        name='admin_dids_edit'),
    path('admin/dids/<int:pk>/del/', views_admin.DidDeleteView.as_view(),
        name='admin_dids_del'),
    path('admin/wallet/credentials/', views_admin.WalletCredentialsView.as_view(),
        name='admin_wallet_credentials'),
    path('admin/wallet/config/issue/', views_admin.WalletConfigIssuesView.as_view(),
        name='admin_wallet_config_issue'),
    path('admin/wallet/config/issue/', views_admin.WalletConfigIssuesView.as_view(),
        name='admin_wallet_config_issue'),
    path('admin/schemas/', views_admin.SchemasView.as_view(),
        name='admin_schemas'),
    path('admin/schemas/<int:pk>/del/', views_admin.SchemasDeleteView.as_view(),
        name='admin_schemas_del'),
    path('admin/schemas/<int:pk>/', views_admin.SchemasDownloadView.as_view(),
        name='admin_schemas_download'),
    path('admin/schemas/new', views_admin.SchemasNewView.as_view(),
        name='admin_schemas_new'),
    path('admin/schemas/import', views_admin.SchemasImportView.as_view(),
        name='admin_schemas_import'),
    path('admin/schemas/import/<str:file_schema>', views_admin.SchemasImportAddView.as_view(),
        name='admin_schemas_import_add'),
    path('admin/import', views_admin.ImportView.as_view(),
        name='admin_import'),
    path('admin/import/new', views_admin.ImportAddView.as_view(),
        name='admin_import_add'),

    # path('verification_portal/verify/', views_verification_portal.verify,
    #      name="verification_portal_verify")
]
