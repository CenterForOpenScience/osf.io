from django.conf.urls import url

from api.view_only_links import views

app_name = 'osf'

urlpatterns = [
    url(r'^(?P<link_id>\w+)/$', views.ViewOnlyLinkDetail.as_view(), name=views.ViewOnlyLinkDetail.view_name),
    url(r'^(?P<link_id>\w+)/nodes/$', views.ViewOnlyLinkNodes.as_view(), name=views.ViewOnlyLinkNodes.view_name),
    url(r'^(?P<link_id>\w+)/relationships/nodes/$', views.ViewOnlyLinkNodesRelationships.as_view(), name=views.ViewOnlyLinkNodesRelationships.view_name),
]
