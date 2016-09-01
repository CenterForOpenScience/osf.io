from django.conf.urls import url
from admin.nodes import views


urlpatterns = [
    url(r'^$', views.NodeFormView.as_view(),
        name='search'),
    url(r'^flagged_spam$', views.NodeFlaggedSpamList.as_view(),
        name='flagged-spam'),
    url(r'^known_spam$', views.NodeKnownSpamList.as_view(),
        name='known-spam'),
    url(r'^(?P<guid>[a-z0-9]+)/$', views.NodeView.as_view(),
        name='node'),
    url(r'^registration_list/$', views.RegistrationListView.as_view(),
        name='registrations'),
    url(r'^(?P<guid>[a-z0-9]+)/remove/$', views.NodeDeleteView.as_view(),
        name='remove'),
    url(r'^(?P<guid>[a-z0-9]+)/restore/$', views.NodeDeleteView.as_view(),
        name='restore'),
    url(r'^(?P<node_id>[a-z0-9]+)/remove_user/(?P<user_id>[a-z0-9]+)/$',
        views.NodeRemoveContributorView.as_view(), name='remove_user'),
]
