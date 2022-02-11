from django.conf.urls import url
from . import views

app_name = 'admin'

urlpatterns = [
    url(r'^$', views.InstitutionEntitlementList.as_view(), name='list'),
    url(r'^add/$', views.AddInstitutionEntitlement.as_view(), name='add'),
    url(r'^(?P<entitlement_id>[0-9]+)/delete/$', views.DeleteInstitutionEntitlement.as_view(), name='delete'),
]
