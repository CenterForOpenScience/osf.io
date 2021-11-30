from django.conf.urls import url

from . import views

app_name = 'admin'

urlpatterns = [
    url(r'^$', views.SpamList.as_view(), name='spam'),
    url(r'^(?P<spam_id>[a-z0-9]+)/$', views.SpamDetail.as_view(), name='detail'),
    url(r'^(?P<spam_id>[a-z0-9]+)/email/$', views.EmailView.as_view(), name='email'),
    url(r'^user/(?P<guid>[a-z0-9]+)/$', views.UserSpamList.as_view(), name='user_spam'),
]
