from django.conf.urls import url
from api.nodes import views

urlpatterns = [
    # Examples:
    # url(r'^$', 'api.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^$', views.NodeList.as_view(), name='node-list'),
    url(r'^(?P<pk>\w+)/$', views.NodeDetail.as_view(), name='node-detail'),
    url(r'^(?P<pk>\w+)/contributors/$', views.NodeContributorsList.as_view(), name='node-contributors'),
    url(r'^(?P<pk>\w+)/registrations/$', views.NodeRegistrationsList.as_view(), name='node-registrations'),
    url(r'^(?P<pk>\w+)/registrations/Open-Ended_Registration$', views.NodeRegistrationsOpenEnded.as_view(), name='node-registration-open-ended'),
    url(r'^(?P<pk>\w+)/registrations/Open-Ended_Registration/(?P<token>\w+)', views.NodeRegistrationsOpenEndedWithToken.as_view(), name='node-registration-open-ended-token'),
    url(r'^(?P<pk>\w+)/registrations/OSF-Standard_Pre-Data_Collection_Registration/$', views.NodeRegistrationsPreDataCollection.as_view(), name='node-registrations-pre-data-collection'),
    url(r'^(?P<pk>\w+)/registrations/OSF-Standard_Pre-Data_Collection_Registration/(?P<token>\w+)', views.NodeRegistrationsPreDataCollectionWithToken.as_view(), name='node-registration-pre-data-collection-token'),
    url(r'^(?P<pk>\w+)/registrations/Replication_Recipe_Pre-Registration/$', views.NodeRegistrationsReplicationRecipePreRegistration.as_view(), name='node-registrations-pre-registration'),
    url(r'^(?P<pk>\w+)/registrations/Replication_Recipe_Pre-Registration/(?P<token>\w+)', views.NodeRegistrationsReplicationRecipePreRegistrationWithToken.as_view(), name='node-registration-pre-registration-token'),
    url(r'^(?P<pk>\w+)/registrations/Replication_Recipe_Post-Completion/$', views.NodeRegistrationsReplicationRecipePostCompletion.as_view(), name='node-registration-post-completion'),
    url(r'^(?P<pk>\w+)/registrations/Replication_Recipe_Post-Completion/(?P<token>\w+)', views.NodeRegistrationsReplicationRecipePostCompletionWithToken.as_view(), name='node-registration-post-completion-token'),
    url(r'^(?P<pk>\w+)/children/$', views.NodeChildrenList.as_view(), name='node-children'),
    url(r'^(?P<pk>\w+)/pointers/$', views.NodePointersList.as_view(), name='node-pointers'),
    url(r'^(?P<pk>\w+)/files/$', views.NodeFilesList.as_view(), name='node-files'),
    url(r'^(?P<pk>\w+)/pointers/(?P<pointer_id>\w+)', views.NodePointerDetail.as_view(), name='node-pointer-detail'),
]
