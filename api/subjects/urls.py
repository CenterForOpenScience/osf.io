from django.urls import re_path

from api.subjects import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^$', views.SubjectList.as_view(), name=views.SubjectList.view_name),
    re_path(r'^(?P<subject_id>\w+)/$', views.SubjectDetail.as_view(), name=views.SubjectDetail.view_name),
    re_path(r'^(?P<subject_id>\w+)/children/$', views.SubjectChildrenList.as_view(), name=views.SubjectChildrenList.view_name),
]
