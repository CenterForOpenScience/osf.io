from django.urls import re_path

from . import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^$', views.CommentList.as_view(), name='comments'),
    re_path(r'^(?P<comment_id>[a-z0-9]+)/$', views.CommentDetail.as_view(), name='comment-detail'),
    re_path(r'^(?P<comment_id>[a-z0-9]+)/mark_spam/$', views.CommentSpamView.as_view(), name='mark-spam'),
    re_path(r'^user/(?P<user_guid>[a-z0-9]+)/$', views.UserCommentList.as_view(), name='user-comment'),
]
