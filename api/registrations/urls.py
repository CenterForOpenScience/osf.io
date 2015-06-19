from django.conf.urls import url
from api.registrations import views

urlpatterns = [
    # Examples:
    # url(r'^$', 'api.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^$', views.NodeRegistrationsAll.as_view(), name='node-registrations-all'),

]
