from django.conf.urls import url

from . import views

app_name = 'osf'

urlpatterns = [
    url(r'^reviews/$', views.ReviewActionList.as_view(), name=views.ReviewActionList.view_name),
    url(r'^(?P<action_id>\w+)/$', views.ActionDetail.as_view(), name=views.ActionDetail.view_name),
]
