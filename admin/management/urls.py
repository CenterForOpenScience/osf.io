from django.urls import re_path

from admin.management import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^$', views.ManagementCommands.as_view(), name='commands'),
    re_path(r'^waffle_flag', views.WaffleFlag.as_view(), name='waffle_flag'),
    re_path(r'^update_registration_schemas',
        views.UpdateRegistrationSchemas.as_view(),
        name='update_registration_schemas'),
    re_path(r'^get_spam_csv', views.GetSpamDataCSV.as_view(), name='get_spam_csv'),
    re_path(r'^ban_spam_regex', views.BanSpamByRegex.as_view(), name='ban_spam_regex'),
    re_path(r'^daily_reporters_go', views.DailyReportersGo.as_view(), name='daily_reporters_go'),
    re_path(r'^monthly_reporters_go', views.MonthlyReportersGo.as_view(), name='monthly_reporters_go'),
    re_path(r'^ingest_cedar_metadata_templates', views.IngestCedarMetadataTemplates.as_view(), name='ingest_cedar_metadata_templates'),
    re_path(r'^bulk_resync', views.BulkResync.as_view(), name='bulk-resync'),
    re_path(r'^empty_metadata_dataarchive_registration_bulk_resync', views.EmptyMetadataDataarchiveRegistrationBulkResync.as_view(),
            name='empty-metadata-dataarchive-registration-bulk-resync')
]
