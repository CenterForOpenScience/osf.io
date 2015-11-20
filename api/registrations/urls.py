from django.conf.urls import url

from api.registrations import views
from api.nodes import views as node_views
from website import settings


urlpatterns = [
    # Examples:
    # url(r'^$', 'api.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^$', views.RegistrationList.as_view(), name=views.RegistrationList.view_name),
    url(r'^(?P<registration_id>\w+)/$', views.RegistrationDetail.as_view(), name=views.RegistrationDetail.view_name),
    url(r'^(?P<node_id>\w+)/contributors/$', node_views.NodeContributorsList.as_view(), name=node_views.NodeContributorsList.view_name),
    url(r'^(?P<node_id>\w+)/contributors/(?P<user_id>\w+)/$', node_views.NodeContributorDetail.as_view(), name=node_views.NodeContributorDetail.view_name),
    url(r'^(?P<node_id>\w+)/children/$', node_views.NodeChildrenList.as_view(), name=node_views.NodeChildrenList.view_name),
    url(r'^(?P<node_id>\w+)/files/$', node_views.NodeProvidersList.as_view(), name=node_views.NodeProvidersList.view_name),
    url(r'^(?P<node_id>\w+)/files/(?P<provider>\w+)(?P<path>/(?:.*/)?)$', node_views.NodeFilesList.as_view(), name=node_views.NodeFilesList.view_name),
    url(r'^(?P<node_id>\w+)/files/(?P<provider>\w+)(?P<path>/.+[^/])$', node_views.NodeFileDetail.as_view(), name=node_views.NodeFileDetail.view_name),
    url(r'^(?P<node_id>\w+)/comments/$', node_views.NodeCommentsList.as_view(), name=node_views.NodeCommentsList.view_name),
]

# Routes only active in local/staging environments
if settings.DEV_MODE:
    urlpatterns.extend([
        url(r'^(?P<node_id>\w+)/node_links/$', node_views.NodeLinksList.as_view(), name=node_views.NodeLinksList.view_name),
        url(r'^(?P<node_id>\w+)/node_links/(?P<node_link_id>\w+)/', node_views.NodeLinksDetail.as_view(), name=node_views.NodeLinksDetail.view_name),
        url(r'^(?P<node_id>\w+)/registrations/$', node_views.NodeRegistrationsList.as_view(), name=node_views.NodeRegistrationsList.view_name),
    ])
