from django.conf.urls import url
from . import views

app_name = 'admin'

urlpatterns = [
    url(r'^$', views.InstitutionEntitlementList.as_view(), name='list'),
]
