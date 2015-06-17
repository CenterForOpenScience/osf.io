from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.UserList.as_view(), name='user-list'),

    url(r'^(?P<user_id>\w+)/$', views.UserDetail.as_view(), name='user-detail'),
    url(r'^(?P<user_id>\w+)/nodes/$', views.UserNodes.as_view(), name='user-nodes'),



]