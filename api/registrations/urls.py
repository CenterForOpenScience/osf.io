from django.conf.urls import url

from api.registrations import views

urlpatterns = [
    # Examples:
    # url(r'^$', 'api.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^$', views.RegistrationList.as_view(), name='registration-list'),
    url(r'^(?P<registration_id>\w+)/$', views.RegistrationDetail.as_view(), name='registration-detail'),
]