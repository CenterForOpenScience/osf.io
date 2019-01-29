from django.conf.urls import url

from api.employment import views

app_name = 'osf'

urlpatterns = [
    url(r'^$', views.EmploymentList.as_view(), name=views.EmploymentList.view_name),
    url(r'^(?P<employment_id>\w+)/$', views.EmploymentDetail.as_view(), name=views.EmploymentDetail.view_name),
]
