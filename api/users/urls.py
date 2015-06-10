from django.conf.urls import url
from . import views


urlpatterns = [
    url(r'^$', views.UserList.as_view(), name='user-list'),
    url(r'^(?P<pk>\w+)/$', views.UserDetail.as_view(), name='user-detail'),  # TODO: Change pk to something else
    url(r'^(?P<pk>\w+)/nodes/$', views.UserNodes.as_view(), name='user-nodes'),
    url(r'^(?P<user_id>\w+)/applications/$', views.ApplicationList.as_view(), name='application-list'),
    url(r'^(?P<user_id>\w+)/applications/(?P<client_id>\w+)/$', views.ApplicationDetail.as_view(), name='application-detail')
]
