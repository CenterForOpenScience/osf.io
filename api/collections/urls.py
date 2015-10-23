from django.conf.urls import url

from api.collections import views
from website import settings

urlpatterns = []

# Routes only active in local/staging environments
if settings.DEV_MODE:
    urlpatterns.extend([
        url(r'^$', views.CollectionList.as_view(), name='collection-list'),
        url(r'^(?P<node_id>\w+)/$', views.CollectionDetail.as_view(), name='collection-detail'),
        url(r'^(?P<node_id>\w+)/node_links/$', views.NodeLinksList.as_view(), name='node-pointers'),
        url(r'^(?P<node_id>\w+)/node_links/(?P<node_link_id>\w+)/', views.NodeLinksDetail.as_view(), name='node-pointer-detail'),
    ])
