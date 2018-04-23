from django.conf.urls import url
from . import views


urlpatterns = [
    url(r'^oauth/accounts/(?P<external_account_id>\w+)/(?P<institution_id>-?[0-9]+)/$', views.OAuthView.as_view(), name='oauth'),
    url(r'^settings/(?P<addon_name>\w+)/(?P<institution_id>-?[0-9]+)/$', views.SettingsView.as_view(), name='settings'),
    url(r'^settings/(?P<addon_name>\w+)/(?P<institution_id>-?[0-9]+)/accounts/$', views.AccountsView.as_view(), name='accounts'),
]