from django.urls import path
from user import views

app_name = 'user'

urlpatterns = [
    path("panel/", views.PanelView.as_view(), name="panel"),
    path("settings/", views.SettingsView.as_view(), name="settings"),
]
