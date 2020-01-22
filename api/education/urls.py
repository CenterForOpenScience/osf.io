from django.conf.urls import url

from api.education import views

app_name = 'osf'

urlpatterns = [
    url(r'^$', views.EducationList.as_view(), name=views.EducationList.view_name),
]
