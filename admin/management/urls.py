from __future__ import absolute_import

from django.conf.urls import url

from admin.management import views

app_name = 'admin'

urlpatterns = [
    url(r'^$', views.ManagementCommands.as_view(), name='commands'),
    url(r'^waffle_flag', views.WaffleFlag.as_view(), name='waffle_flag'),
    url(r'^update_registration_schemas',
        views.UpdateRegistrationSchemas.as_view(),
        name='update_registration_schemas'),
    url(r'^pigeon', views.SendToPigeon.as_view(), name='pigeon'),
    url(r'^create_ia_subcollections', views.CreateIASubcollections.as_view(), name='create_ia_subcollections'),
]
