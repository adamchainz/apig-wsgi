from django.urls import path
from testapp import views

urlpatterns = [
    path("", views.index),
    path("favicon.ico", views.favicon),
]
