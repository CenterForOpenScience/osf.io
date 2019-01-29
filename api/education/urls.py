from django.conf.urls import url

from api.education import views

app_name = 'osf'

urlpatterns = [
    url(r'^$', views.EducationList.as_view(), name=views.EducationList.view_name),
    url(r'^(?P<education_id>\w+)/$', views.EducationDetail.as_view(), name=views.EducationDetail.view_name),
]
