from django.conf.urls import url

urlpatterns = [
    url(r'^prereg/$', 'adminInterface.views.prereg', name='prereg'),
    url(r'^prereg-form/(?P<draft_pk>[0-9a-z]+)/$', 'adminInterface.views.prereg_form', name='prereg_form'),
    url(r'^approve-draft/(?P<draft_pk>[0-9a-z]+)/$', 'adminInterface.views.approve_draft', name='approve_draft'),
    url(r'^reject-draft/(?P<draft_pk>[0-9a-z]+)/$', 'adminInterface.views.reject_draft', name='reject_draft'),
    url(r'^update-draft/(?P<draft_pk>[0-9a-z]+)/$', 'adminInterface.views.update_draft', name='update_draft'),
    url(r'^get-drafts/$', 'adminInterface.views.get_drafts', name='get_drafts'),
    url(r'^get-schemas/$', 'adminInterface.views.get_schemas', name='get_schemas'),
]
