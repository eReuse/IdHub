from api import views

from django.urls import path


app_name = 'api'

urlpatterns = [
    path('v1/snapshot/', views.NewSnapshotView.as_view(), name='new_snapshot'),
    path('v1/annotation/<str:pk>/', views.AddAnnotationView.as_view(), name='new_annotation'),
    path('v1/device/<str:pk>/', views.DetailsDeviceView.as_view(), name='device'),
    path('v1/tokens/', views.TokenView.as_view(), name='tokens'),
    path('v1/tokens/new', views.TokenNewView.as_view(), name='new_token'),
    path("v1/tokens/<int:pk>/edit", views.EditTokenView.as_view(), name="edit_token"),
    path('v1/tokens/<int:pk>/del', views.TokenDeleteView.as_view(), name='delete_token'),
]
