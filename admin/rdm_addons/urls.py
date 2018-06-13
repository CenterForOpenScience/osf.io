from django.conf.urls import include, url
from . import views


urlpatterns = [
    url(r'^$', views.InstitutionListView.as_view(), name='institutions'),
    url(r'^(?P<institution_id>-?[0-9]+)/$', views.AddonListView.as_view(), name='addons'),
    url(r'^allow/(?P<addon_name>\w+)/(?P<institution_id>-?[0-9]+)/(?P<allowed>[01])$', views.AddonAllowView.as_view(), name='allow'),
    url(r'^force/(?P<addon_name>\w+)/(?P<institution_id>-?[0-9]+)/(?P<forced>[01])$', views.AddonForceView.as_view(), name='force'),
    url(r'^icon/(?P<addon_name>\w+)/(?P<icon_filename>\w+\.\w+)$', views.IconView.as_view(), name='icon'),
    url(r'^api/v1/', include('admin.rdm_addons.api_v1.urls', namespace='api_v1')),
    url(r'^oauth/', include('admin.rdm_addons.oauth.urls', namespace='oauth')),
]
