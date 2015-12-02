from django.conf.urls import url

from api.registrations import views

urlpatterns = [
    # Examples:
    # url(r'^$', 'api.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^$', views.RegistrationList.as_view(), name=views.RegistrationList.view_name),
    url(r'^(?P<registration_id>\w+)/$', views.RegistrationDetail.as_view(), name=views.RegistrationDetail.view_name),
]
