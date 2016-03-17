from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.NodeFormView.as_view(),
        name='search'),
    url(r'^id-(?P<guid>[a-z0-9]+)/$', views.NodeView.as_view(),
        name='node'),
    url(r'^registration_list/$', views.RegistrationListView.as_view(),
        name='registrations'),
    url(r'^id-(?P<guid>[a-z0-9]+)/remove_node/$', views.remove_node,
        name='remove_node'),
    url(r'^id-(?P<guid>[a-z0-9]+)/restore_node/$', views.restore_node,
        name='restore_node'),
    url(r'^id-(?P<node_id>[a-z0-9]+)/remove_user-(?P<user_id>[a-z0-9]+)/$',
        views.remove_contributor, name='remove_user'),
]
