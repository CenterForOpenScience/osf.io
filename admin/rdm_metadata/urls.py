from django.conf.urls import url
from . import views


urlpatterns = [
    url(r'^erad$', views.ERadRecordDashboard.as_view(), name='e-rad-records'),
    url(r'^erad/records', views.ERadRecords.as_view(), name='update-e-rad-records'),
]
