from django.conf.urls import url
from . import views

app_name = 'admin'

urlpatterns = [
    # url(r'^$', views.InstitutionEntitlementList.as_view(), name='list'),
    url(r'^bulk_add/$', views.BulkAddInstitutionEntitlement.as_view(), name='bulk_add'),
    # url(r'^(?P<entitlement_id>[0-9]+)/toggle/$', views.ToggleInstitutionEntitlement.as_view(http_method_names=['post']), name='toggle'),
    # url(r'^(?P<entitlement_id>[0-9]+)/delete/$', views.DeleteInstitutionEntitlement.as_view(http_method_names=['post']), name='delete'),
]
