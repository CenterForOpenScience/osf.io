from django.conf.urls import url

from admin.desk import views

app_name = 'admin'

urlpatterns = [
    url(r'^customer/(?P<guid>[a-z0-9]+)/$', views.DeskCustomer.as_view(), name='customer'),
    url(r'^cases/(?P<guid>[a-z0-9]+)/$', views.DeskCaseList.as_view(), name='user_cases'),
]
