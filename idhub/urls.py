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
    path('admin/people/<int:pk>/membership/new/', views_admin.AdminPeopleMembershipRegisterView.as_view(),
        name='admin_people_membership_new'),
    path('admin/membership/<int:pk>/edit/', views_admin.AdminPeopleMembershipEditView.as_view(),
        name='admin_people_membership_edit'),
    path('admin/membership/<int:pk>/del/', views_admin.AdminPeopleMembershipDeleteView.as_view(),
        name='admin_people_membership_del'),
    path('admin/people/<int:pk>/rol/new/', views_admin.AdminPeopleRolRegisterView.as_view(),
        name='admin_people_rol_new'),
    path('admin/people/<int:pk>/rol/edit/', views_admin.AdminPeopleRolEditView.as_view(),
        name='admin_people_rol_edit'),
    path('admin/people/<int:pk>/rol/del/', views_admin.AdminPeopleRolDeleteView.as_view(),
        name='admin_people_rol_del'),
    path('admin/roles/', views_admin.AdminRolesView.as_view(),
        name='admin_roles'),
    path('admin/roles/new', views_admin.AdminRolRegisterView.as_view(),
        name='admin_rol_new'),
    path('admin/roles/<int:pk>', views_admin.AdminRolEditView.as_view(),
        name='admin_rol_edit'),
    path('admin/roles/<int:pk>/del', views_admin.AdminRolDeleteView.as_view(),
        name='admin_rol_del'),
    path('admin/services/', views_admin.AdminServicesView.as_view(),
        name='admin_services'),
    path('admin/services/new', views_admin.AdminServiceRegisterView.as_view(),
        name='admin_service_new'),
    path('admin/services/<int:pk>', views_admin.AdminServiceEditView.as_view(),
        name='admin_service_edit'),
    path('admin/services/<int:pk>/del', views_admin.AdminServiceDeleteView.as_view(),
        name='admin_service_del'),
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
    path('admin/schemas/', views_admin.AdminSchemasView.as_view(),
        name='admin_schemas'),
    path('admin/schemas/<int:pk>/del/', views_admin.AdminSchemasDeleteView.as_view(),
        name='admin_schemas_del'),
    path('admin/schemas/<int:pk>/', views_admin.AdminSchemasDownloadView.as_view(),
        name='admin_schemas_download'),
    path('admin/schemas/new', views_admin.AdminSchemasNewView.as_view(),
        name='admin_schemas_new'),
    path('admin/schemas/import', views_admin.AdminSchemasImportView.as_view(),
        name='admin_schemas_import'),
    path('admin/schemas/import/<str:file_schema>', views_admin.AdminSchemasImportAddView.as_view(),
        name='admin_schemas_import_add'),
    path('admin/import', views_admin.AdminImportView.as_view(),
        name='admin_import'),
    path('admin/import/new', views_admin.AdminImportStep2View.as_view(),
        name='admin_import_step2'),
    path('admin/import/<int:pk>/', views_admin.AdminImportStep3View.as_view(),
        name='admin_import_step3'),
]
