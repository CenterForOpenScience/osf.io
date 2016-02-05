from django.conf.urls import url
from api.comments import views

urlpatterns = [
    url(r'^(?P<comment_id>\w+)/$', views.CommentDetail.as_view(), name=views.CommentDetail.view_name),
    url(r'^(?P<comment_id>\w+)/reports/$', views.CommentReportsList.as_view(), name=views.CommentReportsList.view_name),
    url(r'^(?P<comment_id>\w+)/reports/(?P<user_id>\w+)/$', views.CommentReportDetail.as_view(), name=views.CommentReportDetail.view_name),
]
