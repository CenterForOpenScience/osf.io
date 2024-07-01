from django.urls import re_path
from api.comments import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^(?P<comment_id>\w+)/$', views.CommentDetail.as_view(), name=views.CommentDetail.view_name),
    re_path(r'^(?P<comment_id>\w+)/reports/$', views.CommentReportsList.as_view(), name=views.CommentReportsList.view_name),
    re_path(r'^(?P<comment_id>\w+)/reports/(?P<user_id>\w+)/$', views.CommentReportDetail.as_view(), name=views.CommentReportDetail.view_name),
]
