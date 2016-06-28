from django.conf.urls import url

from api.collections import views

urlpatterns = [
    url(r'^$', views.CollectionList.as_view(), name=views.CollectionList.view_name),
    url(r'^(?P<collection_id>\w+)/$', views.CollectionDetail.as_view(), name=views.CollectionDetail.view_name),
    url(r'^(?P<collection_id>\w+)/linked_nodes/$', views.LinkedNodesList.as_view(), name=views.LinkedNodesList.view_name),
    url(r'^(?P<collection_id>\w+)/linked_registrations/$', views.LinkedRegistrationsList.as_view(), name=views.LinkedRegistrationsList.view_name),
    url(r'^(?P<collection_id>\w+)/node_links/$', views.NodeLinksList.as_view(), name=views.NodeLinksList.view_name),
    url(r'^(?P<collection_id>\w+)/node_links/(?P<node_link_id>\w+)/', views.NodeLinksDetail.as_view(), name=views.NodeLinksDetail.view_name),
    url(r'^(?P<collection_id>\w+)/relationships/linked_nodes/$', views.CollectionLinkedNodesRelationship.as_view(), name=views.CollectionLinkedNodesRelationship.view_name),
    url(r'^(?P<collection_id>\w+)/relationships/linked_registrations/$', views.CollectionLinkedRegistrationsRelationship.as_view(), name=views.CollectionLinkedRegistrationsRelationship.view_name),
]
