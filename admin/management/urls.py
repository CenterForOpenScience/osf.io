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
    url(r'^get_spam_csv', views.GetSpamDataCSV.as_view(), name='get_spam_csv'),
    url(r'^ban_spam_regex', views.BanSpamByRegex.as_view(), name='ban_spam_regex'),
    url(r'^migrate_quickfiles', views.MigrateQuickfiles.as_view(), name='migrate_quickfiles'),
    url(r'^reindex_quickfiles', views.ReindexQuickfiles.as_view(), name='reindex_quickfiles'),
]
