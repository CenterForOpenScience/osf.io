from django.conf.urls import url
from django.contrib.auth.decorators import login_required as login

from . import views

urlpatterns = [
    url(r'^$', views.DraftListView.as_view(), name='prereg'),
    url(
        r'^drafts/(?P<draft_pk>[0-9a-z]+)/$',
        views.DraftDetailView.as_view(),
        name='view_draft'
    ),
    url(
        r'^drafts/(?P<draft_pk>[0-9a-z]+)/update/$',
        login(views.update_draft),
        name='update_draft'
    ),
    url(
        r'^drafts/(?P<draft_pk>[0-9a-z]+)/approve/$',
        login(views.approve_draft),
        name='approve_draft'
    ),
    url(
        r'^drafts/(?P<draft_pk>[0-9a-z]+)/reject/$',
        login(views.reject_draft),
        name='reject_draft'
    ),
    url(
        r'^(?P<node_id>[a-zA-Z0-9]{5})/files/(?P<provider>.+?)/(?P<file_id>.+)/?',
        login(views.view_file),
        name='view_file'
    )
]
