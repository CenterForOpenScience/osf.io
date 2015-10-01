from django.conf.urls import url

from api.nodes import views as node_views
from api.comments import views

urlpatterns = [
    url(r'^(?P<comment_id>\w+)/$', views.CommentDetail.as_view(), name='comment-detail'),
    url(r'^(?P<comment_id>\w+)/replies/$', node_views.CommentRepliesList.as_view(), name='comment-replies'),
    url(r'^(?P<comment_id>\w+)/reports/$', views.CommentReports.as_view(), name='comment-reports'),

]
