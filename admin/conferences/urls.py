from django.conf.urls import url
from views import ConfDetailView, ConfFormView, ConfListView
from django.views.decorators.http import require_POST

from . import views

urlpatterns = [
    url(r'^$', views.create_conference, name='create_conference'),
    url(r'^conference/(?P<pk>\d+)/$', ConfDetailView.as_view(), name='my_detail_view_url'),
	url(r'^conference_form/$', require_POST(ConfFormView.as_view()), name='my_form_view_url'),
	url(r'^conf_to_osf/$', views.add_conference_to_OSF, name='add_conference_to_OSF'),
	url(r'^conference_list$', ConfListView.as_view(), name='conference_list'),
]
