from django.conf.urls import url

from api.registrations import views
from website import settings


urlpatterns = [
    # Examples:
    # url(r'^$', 'api.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^$', views.RegistrationList.as_view(), name=views.RegistrationList.view_name),
    url(r'^(?P<node_id>\w+)/$', views.RegistrationDetail.as_view(), name=views.RegistrationDetail.view_name),
    url(r'^(?P<node_id>\w+)/contributors/$', views.RegistrationContributorsList.as_view(), name=views.RegistrationContributorsList.view_name),
    url(r'^(?P<node_id>\w+)/contributors/(?P<user_id>\w+)/$', views.RegistrationContributorDetail.as_view(), name=views.RegistrationContributorDetail.view_name),
    url(r'^(?P<node_id>\w+)/children/$', views.RegistrationChildrenList.as_view(), name=views.RegistrationChildrenList.view_name),
    url(r'^(?P<node_id>\w+)/forks/$', views.RegistrationForksList.as_view(), name=views.RegistrationForksList.view_name),
    url(r'^(?P<node_id>\w+)/files/$', views.RegistrationProvidersList.as_view(), name=views.RegistrationProvidersList.view_name),
    url(r'^(?P<node_id>\w+)/files/(?P<provider>\w+)(?P<path>/(?:.*/)?)$', views.RegistrationFilesList.as_view(), name=views.RegistrationFilesList.view_name),
    url(r'^(?P<node_id>\w+)/files/(?P<provider>\w+)(?P<path>/.+[^/])$', views.RegistrationFileDetail.as_view(), name=views.RegistrationFileDetail.view_name),
    url(r'^(?P<node_id>\w+)/citations/$', views.RegistrationAlternativeCitationsList.as_view(), name=views.RegistrationAlternativeCitationsList.view_name),
    url(r'^(?P<node_id>\w+)/citations/(?P<citation_id>\w+)/$', views.RegistrationAlternativeCitationDetail.as_view(), name=views.RegistrationAlternativeCitationDetail.view_name),
    url(r'^(?P<node_id>\w+)/comments/$', views.RegistrationCommentsList.as_view(), name=views.RegistrationCommentsList.view_name),
    url(r'^(?P<node_id>\w+)/logs/$', views.RegistrationLogList.as_view(), name=views.RegistrationLogList.view_name),
    url(r'^(?P<node_id>\w+)/institution/$', views.RegistrationInstitutionDetail.as_view(), name=views.RegistrationInstitutionDetail.view_name),
    url(r'^(?P<node_id>\w+)/node_links/$', views.RegistrationNodeLinksList.as_view(), name=views.RegistrationNodeLinksList.view_name),
    url(r'^(?P<node_id>\w+)/node_links/(?P<node_link_id>\w+)/', views.RegistrationNodeLinksDetail.as_view(), name=views.RegistrationNodeLinksDetail.view_name),
    url(r'^(?P<node_id>\w+)/wikis/$', views.RegistrationWikiList.as_view(), name=views.RegistrationWikiList.view_name),
    url(r'^(?P<node_id>\w+)/wikis/(?P<wiki_id>\w+)/', views.RegistrationWikiDetail.as_view(), name=views.RegistrationWikiDetail.view_name),
]

# Routes only active in local/staging environments
if settings.DEV_MODE:
    urlpatterns.extend([
        url(r'^(?P<node_id>\w+)/registrations/$', views.RegistrationRegistrationsList.as_view(), name=views.RegistrationRegistrationsList.view_name),
    ])
