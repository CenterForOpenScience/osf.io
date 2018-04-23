from django.conf.urls import url
from . import views


urlpatterns = [
    url(r'^$', views.InstitutionList.as_view(), name='institutions'),
    url(r'^(?P<institution_id>[0-9]+)/$', views.RemoveUserKeyList.as_view(), name='users'),
    url(r'^(?P<institution_id>[0-9]+)/delete/(?P<user_id>[0-9]+)/$', views.RemoveUserKey.as_view(), name='user_key_delete'),
]
