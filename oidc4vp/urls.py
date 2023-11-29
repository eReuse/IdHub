from django.urls import path, reverse_lazy

from oidc4vp import views


app_name = 'oidc4vp'


urlpatterns = [
    path('verify', views.VerifyView.as_view(),
         name="verify"),
    path('authorization', views.AuthorizationView.as_view(),
         name="authorization"),
]
