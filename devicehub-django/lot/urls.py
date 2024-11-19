from django.urls import path
from lot import views

app_name = 'lot'

urlpatterns = [
    path("add/", views.NewLotView.as_view(), name="add"),
    path("delete/<int:pk>/", views.DeleteLotView.as_view(), name="delete"),
    path("edit/<int:pk>/", views.EditLotView.as_view(), name="edit"),
    path("add/devices/", views.AddToLotView.as_view(), name="add_devices"),
    path("del/devices/", views.DelToLotView.as_view(), name="del_devices"),
    path("tag/<int:pk>/", views.LotsTagsView.as_view(), name="tag"),
    path("<int:pk>/document/", views.LotDocumentsView.as_view(), name="documents"),
    path("<int:pk>/document/add", views.LotAddDocumentView.as_view(), name="add_document"),
    path("<int:pk>/annotation", views.LotAnnotationsView.as_view(), name="annotations"),
    path("<int:pk>/annotation/add", views.LotAddAnnotationView.as_view(), name="add_annotation"),
]
