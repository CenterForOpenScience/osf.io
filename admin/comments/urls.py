from django.conf.urls import url

from . import views

app_name = 'admin'

urlpatterns = [
    url(r'^$', views.CommentList.as_view(), name='comments'),
    url(r'^(?P<comment_id>[a-z0-9]+)/$', views.CommentDetail.as_view(), name='comment-detail'),
    url(r'^(?P<comment_id>[a-z0-9]+)/mark_spam/$', views.CommentSpamView.as_view(), name='mark-spam'),
    url(r'^user/(?P<user_guid>[a-z0-9]+)/$', views.UserCommentList.as_view(), name='user-comment'),
]
