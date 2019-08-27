from django.conf.urls import url
from . import views

app_name = 'quota_recalc'

urlpatterns = [
    url(r'^$', views.all_users, name='all_users'),
    url(r'^(?P<guid>[a-z0-9]+)/$', views.user, name='user'),
]
