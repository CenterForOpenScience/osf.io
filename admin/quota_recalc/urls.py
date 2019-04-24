from django.conf.urls import url
from . import views

app_name = 'admin'

urlpatterns = [
    url(r'^(?P<user_id>\w+)/$', views.by_user_id, name='by_user_id'),
    url(r'^$', views.index, name='index'),
]
