from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.prereg, name='prereg'),
    url(r'^drafts/(?P<draft_pk>[0-9a-z]+)/$', views.prereg_form, name='prereg_form'),
    url(r'^drafts/(?P<draft_pk>[0-9a-z]+)/approve/$', views.approve_draft, name='approve_draft'),
    url(r'^drafts/(?P<draft_pk>[0-9a-z]+)/reject/$', views.reject_draft, name='reject_draft'),
    url(r'^drafts/(?P<draft_pk>[0-9a-z]+)/update/$', views.update_draft, name='update_draft'),
    url(r'^drafts/$', views.get_drafts, name='get_drafts')
]
