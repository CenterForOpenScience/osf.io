from django.conf.urls import url
from api.registrations import views

urlpatterns = [
    # Examples:
    # url(r'^$', 'api.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^$', views.RegistrationList.as_view(), name='registration-list'),
    url(r'^(?P<draft_id>\w+)/$', views.RegistrationCreate.as_view(), name='registration-detail'),
    url(r'^(?P<draft_id>\w+)/freeze/(?P<token>\w+)/$', views.RegistrationCreateWithToken.as_view(), name='registration-create'),
]
