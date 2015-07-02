from django.conf.urls import url
from api.registrations import views

urlpatterns = [
    # Examples:
    # url(r'^$', 'api.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^$', views.RegistrationList.as_view(), name='registration-list'),
    url(r'^(?P<registration_id>\w+)/$', views.RegistrationDetail.as_view(), name='registration-detail'),
    url(r'^(?P<registration_id>\w+)/freeze/(?P<token>\w+)/$', views.RegistrationCreate.as_view(), name='registration-create'),
    url(r'^(?P<registration_id>\w+)/contributors/$', views.RegistrationContributorsList.as_view(), name='registration-contributors'),
    url(r'^(?P<registration_id>\w+)/children/$', views.RegistrationChildrenList.as_view(), name='registration-children'),
    url(r'^(?P<registration_id>\w+)/pointers/$', views.RegistrationPointersList.as_view(), name='registration-pointers'),
    url(r'^(?P<registration_id>\w+)/files/$', views.RegistrationFilesList.as_view(), name='registration-files'),

]
