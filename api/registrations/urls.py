from django.conf.urls import url

from api.registrations import views
from api.nodes import views as node_views
from website import settings


urlpatterns = [
    # Examples:
    # url(r'^$', 'api.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^$', views.RegistrationList.as_view(), name='registration-list'),
    url(r'^(?P<registration_id>\w+)/$', views.RegistrationDetail.as_view(), name='registration-detail'),
    url(r'^(?P<node_id>\w+)/contributors/$', node_views.NodeContributorsList.as_view(), name='registration-contributors'),
    url(r'^(?P<node_id>\w+)/contributors/(?P<user_id>\w+)/$', node_views.NodeContributorDetail.as_view(), name='registration-contributor-detail'),
    url(r'^(?P<node_id>\w+)/children/$', node_views.NodeChildrenList.as_view(), name='registration-children'),
    url(r'^(?P<node_id>\w+)/files/$', node_views.NodeProvidersList.as_view(), name='registration-providers'),
    url(r'^(?P<node_id>\w+)/files/(?P<provider>\w+)(?P<path>/(?:.*/)?)$', node_views.NodeFilesList.as_view(), name='registration-files'),
    url(r'^(?P<node_id>\w+)/files/(?P<provider>\w+)(?P<path>/.+[^/])$', node_views.NodeFileDetail.as_view(), name='registration-file-detail'),
]

# Routes only active in local/staging environments
if settings.DEV_MODE:
    urlpatterns.extend([
        url(r'^(?P<node_id>\w+)/node_links/$', node_views.NodeLinksList.as_view(), name='registration-pointers'),
        url(r'^(?P<node_id>\w+)/node_links/(?P<node_link_id>\w+)/', node_views.NodeLinksDetail.as_view(), name='registration-pointer-detail'),
        url(r'^(?P<node_id>\w+)/registrations/$', node_views.NodeRegistrationsList.as_view(), name='registration-registrations'),
    ])

