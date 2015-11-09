from django.conf.urls import url
from api.comments import views

urlpatterns = [
    url(r'^(?P<comment_id>\w+)/$', views.CommentDetail.as_view(), name='comment-detail'),
    url(r'^(?P<comment_id>\w+)/replies/$', views.CommentRepliesList.as_view(), name='comment-replies'),
    url(r'^(?P<comment_id>\w+)/reports/$', views.CommentReportsList.as_view(), name='comment-reports'),
    url(r'^(?P<comment_id>\w+)/reports/(?P<user_id>\w+)/$', views.CommentReportDetail.as_view(), name='report-detail'),
]
