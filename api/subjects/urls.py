from django.conf.urls import url

from api.subjects import views

app_name = 'osf'

urlpatterns = [
    url(r'^(?P<subject_id>\w+)/$', views.SubjectDetail.as_view(), name=views.SubjectDetail.view_name),
    url(r'^(?P<subject_id>\w+)/children/$', views.SubjectChildrenList.as_view(), name=views.SubjectChildrenList.view_name),
]
