from webhook import views

from django.urls import path


app_name = 'webhook'

urlpatterns = [
    path('verify/', views.webhook_verify, name='verify'),
    path('sign/', views.webhook_issue, name='sign'),
    path('tokens/', views.WebHookTokenView.as_view(), name='tokens'),
    path('tokens/new', views.TokenNewView.as_view(), name='new_token'),
    path('tokens/<int:pk>/del', views.TokenDeleteView.as_view(), name='delete_token'),
    path('tokens/<int:pk>/status', views.TokenStatusView.as_view(), name='status_token'),
]
