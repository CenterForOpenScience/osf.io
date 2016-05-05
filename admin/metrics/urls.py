from django.conf.urls import url
from django.contrib.auth.decorators import login_required as login

from . import views

urlpatterns = [
    url(r'^$', login(views.OSFStatisticsListView.as_view()), name='stats_list'),
    url(r'^update/$', login(views.update_metrics), name='update'),
    url(r'^download/$', login(views.download_csv), name='download'),
]
