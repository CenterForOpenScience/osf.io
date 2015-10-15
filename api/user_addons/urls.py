from django.conf.urls import url
from . import views

ROUTE_BASE = r'^(?P<user_addon_id>\w+)/'

urlpatterns = [
    url(ROUTE_BASE + '$', views.UserAddonDetail.as_view(), name='user-addon-detail'),
    url(ROUTE_BASE + 'external_accounts/$', views.UserAddonAccountList.as_view(), name='user-addon-external-accounts'),
    url(ROUTE_BASE + 'external_accounts/(?P<external_account_id>\w+)/$', views.UserAddonAccountDetail.as_view(), name='user-addon-external-account-detail'),
    url(ROUTE_BASE + 'nodes/$', views.UserAddonNodeList.as_view(), name='user-addon-nodes'),
    url(ROUTE_BASE + 'nodes/(?P<node_id>\w+)/$', views.UserAddonNodeDetail.as_view(), name='user-addon-node-detail'),
]
