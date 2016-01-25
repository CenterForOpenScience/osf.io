from django.conf.urls import url
from api.reports import views

urlpatterns = [
    url(r'^(?P<guid>\w+)/reports/$', views.CommentReportsList.as_view(), name=views.CommentReportsList.view_name),
    url(r'^(?P<guid>\w+)/reports/(?P<user_id>\w+)/$', views.CommentReportDetail.as_view(), name=views.CommentReportDetail.view_name),
]
