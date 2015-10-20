from django.conf.urls import url
from . import views

ROUTE_BASE = r'^(?P<node_addon_id>\w+)/'

urlpatterns = [
    url(ROUTE_BASE + '$', views.NodeAddonDetail.as_view(), name='node-addon-detail'),
]
