from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from django.urls import path, reverse_lazy
from login.views import (
    LoginView,
    LogoutView,
    PasswordResetView,
    PasswordResetConfirmView,
)

app_name = 'login'

urlpatterns = [
    path("", RedirectView.as_view(url=reverse_lazy('login:login'),
        permanent=False)),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView, name='logout'),
    path('auth/password_reset/', PasswordResetView.as_view(), name='password_reset'),
    path('auth/password_reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='password_reset_done.html'
        ),
        name='password_reset_done'
    ),
    path('auth/reset/<uidb64>/<token>/', PasswordResetConfirmView.as_view(),
        name='password_reset_confirm'
    ),
    path('auth/reset/done/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='password_reset_complete.html'
        ),
        name='password_reset_complete'
    ),
]
