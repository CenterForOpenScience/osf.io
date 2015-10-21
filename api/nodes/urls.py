from django.conf.urls import url

from api.nodes import views
from website import settings

urlpatterns = [
    # Examples:
    # url(r'^$', 'api.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^$', views.NodeList.as_view(), name='node-list'),
    url(r'^(?P<node_id>\w+)/$', views.NodeDetail.as_view(), name='node-detail'),
    url(r'^(?P<node_id>\w+)/contributors/$', views.NodeContributorsList.as_view(), name='node-contributors'),
    url(r'^(?P<node_id>\w+)/contributors/(?P<user_id>\w+)/$', views.NodeContributorDetail.as_view(), name='node-contributor-detail'),
    url(r'^(?P<node_id>\w+)/children/$', views.NodeChildrenList.as_view(), name='node-children'),
    url(r'^(?P<node_id>\w+)/files/$', views.NodeProvidersList.as_view(), name='node-providers'),
    url(r'^(?P<node_id>\w+)/files/(?P<provider>\w+)(?P<path>/(?:.*/)?)$', views.NodeFilesList.as_view(), name='node-files'),
    url(r'^(?P<node_id>\w+)/files/(?P<provider>\w+)(?P<path>/.+[^/])$', views.NodeFileDetail.as_view(), name='node-file-detail'),
    url(r'^(?P<node_id>\w+)/comments/$', views.NodeCommentsList.as_view(), name='node-comments'),
]

# Routes only active in local/staging environments
if settings.DEV_MODE:
    urlpatterns.extend([
        url(r'^(?P<node_id>\w+)/node_links/$', views.NodeLinksList.as_view(), name='node-pointers'),
        url(r'^(?P<node_id>\w+)/node_links/(?P<node_link_id>\w+)/', views.NodeLinksDetail.as_view(), name='node-pointer-detail'),
        url(r'^(?P<node_id>\w+)/registrations/$', views.NodeRegistrationsList.as_view(), name='node-registrations'),
    ])
