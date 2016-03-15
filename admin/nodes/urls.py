from django.conf.urls import url
from django.contrib.auth.decorators import login_required as login

from . import views

# TODO: Replace login_required with decorators and mix-ins (1.9)

urlpatterns = [
    url(r'^$', login(views.NodeFormView.as_view()),
        name='search'),
    url(r'^id-(?P<guid>[a-z0-9]+)/$', login(views.NodeView.as_view()),
        name='node'),
    url(r'^registration_list/$', login(views.RegistrationListView.as_view()),
        name='registrations'),
    url(r'^id-(?P<guid>[a-z0-9]+)/remove_node/$', login(views.remove_node),
        name='remove_node'),
    url(r'^id-(?P<guid>[a-z0-9]+)/restore_node/$', login(views.restore_node),
        name='restore_node'),
]
