from django.conf.urls import url
from api.draft_registrations import views

urlpatterns = [
    url(r'^$', views.DraftRegistrationList.as_view(), name='registration-list'),
    url(r'^(?P<registration_id>\w+)/$', views.DraftRegistrationDetail.as_view(), name='registration-detail'),
    url(r'^(?P<registration_id>\w+)/freeze/(?P<token>\w+)/$', views.DraftRegistrationCreate.as_view(), name='registration-create'),
    url(r'^(?P<registration_id>\w+)/contributors/$', views.DraftRegistrationContributorsList.as_view(), name='registration-contributors'),
    url(r'^(?P<registration_id>\w+)/children/$', views.DraftRegistrationChildrenList.as_view(), name='registration-children'),
    url(r'^(?P<registration_id>\w+)/pointers/$', views.DraftRegistrationPointersList.as_view(), name='registration-pointers'),
    url(r'^(?P<registration_id>\w+)/files/$', views.DraftRegistrationFilesList.as_view(), name='registration-files'),

]
