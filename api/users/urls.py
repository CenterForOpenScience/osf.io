from django.conf.urls import include, url
from . import views

# Define endpoints to exclude from swagger documentation
internal_apis = [
    url(r'^(?P<user_id>\w+)/applications/$', views.ApplicationList.as_view(), name='application-list'),
    url(r'^(?P<user_id>\w+)/applications/(?P<client_id>\w+)/$', views.ApplicationDetail.as_view(), name='application-detail')
]

urlpatterns = [
    url(r'^$', views.UserList.as_view(), name='user-list'),
    url(r'^(?P<pk>\w+)/$', views.UserDetail.as_view(), name='user-detail'),
    url(r'^(?P<pk>\w+)/nodes/$', views.UserNodes.as_view(), name='user-nodes'),
    url(r'^', include(internal_apis, namespace='internal_apis'))
]
