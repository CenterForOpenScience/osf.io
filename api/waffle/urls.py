from django.conf.urls import url
from . import views


urlpatterns = [
    url(r'^$', views.WaffleList.as_view(), name=views.WaffleList.view_name),
]
