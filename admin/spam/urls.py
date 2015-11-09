from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.spam_list, name='spam'),
    url(r'^(?P<spam_id>[a-z0-9]+)/$', views.spam_detail, name='detail'),
    url(r'^details/$', views.spam_sub_list, name='sub_list'),
    url(r'^(?P<spam_id>[a-z0-9]+)/email/$', views.email, name='email'),
]
