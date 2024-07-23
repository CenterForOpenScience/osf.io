from django.urls import re_path
from . import views


urlpatterns = [
    re_path(r'^$', views.WaffleList.as_view(), name=views.WaffleList.view_name),
]
