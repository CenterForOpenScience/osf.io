from django.conf.urls import url

from api.employment import views

app_name = 'osf'

urlpatterns = [
    url(r'^$', views.EmploymentList.as_view(), name=views.EmploymentList.view_name),
]
