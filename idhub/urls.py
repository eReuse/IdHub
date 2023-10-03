from django.urls import path
from . import views

app_name = 'idhub'

urlpatterns = [
    # path("", views.index, name="index"),
    path('login/', views.LoginView.as_view(), name='login'),
    path('user/dashboard/', views.UserDashboardView.as_view(), name='user_dashboard'),
]
