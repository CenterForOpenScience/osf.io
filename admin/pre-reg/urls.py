from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.prereg, name='prereg'),
    url(r'^prereg_form/(?P<draft_pk>[0-9a-z]+)/$', views.prereg_form, name='prereg_form'),
    url(r'^approve_draft/(?P<draft_pk>[0-9a-z]+)/$', views.approve_draft, name='approve_draft'),
    url(r'^reject_draft/(?P<draft_pk>[0-9a-z]+)/$', views.reject_draft, name='reject_draft'),
    url(r'^update_draft/(?P<draft_pk>[0-9a-z]+)/$', views.update_draft, name='update_draft'),
    url(r'^get_drafts/$', views.get_drafts, name='get_drafts'),
    url(r'^get_schemas/$', views.get_schemas, name='get_schemas'),
]
