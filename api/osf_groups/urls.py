from django.conf.urls import url

from api.osf_groups import views

app_name = 'osf'

urlpatterns = [
    url(r'^$', views.GroupList.as_view(), name=views.GroupList.view_name),
    url(r'^(?P<group_id>\w+)/$', views.GroupDetail.as_view(), name=views.GroupDetail.view_name),
    url(r'^(?P<group_id>\w+)/members/$', views.GroupMembersList.as_view(), name=views.GroupMembersList.view_name),
    url(r'^(?P<group_id>\w+)/members/(?P<user_id>\w+)/$', views.GroupMemberDetail.as_view(), name=views.GroupMemberDetail.view_name),
]
