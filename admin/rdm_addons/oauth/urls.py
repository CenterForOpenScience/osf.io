from django.conf.urls import url
from . import views


urlpatterns = [
    url(r'^connect/(?P<addon_name>\w+)/(?P<institution_id>-?[0-9]+)/$', views.ConnectView.as_view(), name='connect'),
    url(r'^callback/(?P<addon_name>\w+)/$', views.CallbackView.as_view(), name='callback'),
    url(r'^complete/(?P<addon_name>\w+)/$', views.CompleteView.as_view(), name='complete'),
    url(r'^accounts/(?P<external_account_id>\w+)/(?P<institution_id>-?[0-9]+)/$', views.AccountsView.as_view(), name='disconnect'),
]