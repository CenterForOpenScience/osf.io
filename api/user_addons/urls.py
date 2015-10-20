from django.conf.urls import url
from . import views

ROUTE_BASE = r'^(?P<user_addon_id>\w+)/'

urlpatterns = [
    url(ROUTE_BASE + '$', views.UserAddonDetail.as_view(), name='user-addon-detail'),
    url(ROUTE_BASE + 'external_accounts/$', views.UserAddonAccountList.as_view(), name='user-addon-external-accounts'),
    url(ROUTE_BASE + 'external_accounts/(?P<external_account_id>\w+)/$', views.UserAddonAccountDetail.as_view(), name='user-addon-external-account-detail'),
    url(ROUTE_BASE + 'linked_nodes/$', views.UserAddonNodeAddonList.as_view(), name='user-addon-node-addons'),
    url(ROUTE_BASE + 'linked_nodes/(?P<node_addon_id>\w+)/$', views.UserAddonNodeAddonDetail.as_view(), name='user-addon-node-addon-detail'),
]
