from django.urls import path, reverse_lazy

from promotion import views


app_name = 'promotion'


urlpatterns = [
    path('', views.PromotionView.as_view(),
         name="show_promotion"),
    path('select_wallet', views.SelectWalletView.as_view(),
         name="select_wallet"),
]
