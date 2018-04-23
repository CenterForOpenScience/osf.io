from django.conf.urls import url
from . import views


urlpatterns = [
    url(r'^$', views.InstitutionListViewStat.as_view(), name='institutions'),
    url(r'^(?P<institution_id>-?[0-9]+)/$', views.StatisticsView.as_view(), name='statistics'),
    url(r'^index$', views.IndexView.as_view(), name='index'),
    url(r'^(?P<institution_id>-?[0-9]+)/graph/(?P<graph_type>\w+)_(?P<provider>\w+)\.(\w+)$',
        views.ImageView.as_view(), name='graph'),
    url(r'^gather/(?P<access_token>-?\w+)/$', views.GatherView.as_view(), name='gather'),
    url(r'^report/(?P<institution_id>-?[0-9]+)/$', views.create_pdf, name='report'),
    url(r'^csv/(?P<institution_id>-?[0-9]+)/$', views.create_csv, name='csv'),
    url(r'^mail/(?P<institution_id>-?[0-9]+)/$', views.SendView.as_view(), name='mail'),
    url(r'^dummy/(?P<institution_id>-?[0-9]+)/$', views.DummyCreateView.as_view(), name='dummy'),
    url(r'^test/mail/$', views.send_stat_mail, name='test'),
]
