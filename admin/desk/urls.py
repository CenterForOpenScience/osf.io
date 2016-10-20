from django.conf.urls import url

from admin.desk import views

urlpatterns = [
    url(r'^customer/(?P<user_id>[a-z0-9]+)/$', views.DeskCustomer.as_view(),
        name='customer'),
    url(r'^cases/(?P<user_id>[a-z0-9]+)/$', views.DeskCaseList.as_view(),
        name='user_cases'),
]
