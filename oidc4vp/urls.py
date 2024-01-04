from django.urls import path, reverse_lazy

from oidc4vp import views


app_name = 'oidc4vp'


urlpatterns = [
    path('verify', views.VerifyView.as_view(),
         name="verify"),
    path('authorize', views.AuthorizeView.as_view(),
         name="authorize"),
    path('allow_code', views.AllowCodeView.as_view(),
         name="allow_code"),
]
