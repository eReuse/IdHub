from django.urls import path
from did import views

app_name = 'did'

urlpatterns = [
    path("<str:pk>", views.PublicDeviceWebView.as_view(), name="device_web"),
]
