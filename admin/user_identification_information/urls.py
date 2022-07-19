from django.conf.urls import url

from . import views

app_name = 'admin'

urlpatterns = [
    url(r'^$', views.ShowListUser.as_view(), name='index'),
    url(r'^(?P<guid>[a-z0-9]+)/$', views.UserView.as_view(), name='details'),
]
