from django.conf.urls import url

from api.comments import views

urlpatterns = [
    url(r'^(?P<comment_id>\w+)/$', views.CommentDetail.as_view(), name='comment-detail'),
]
