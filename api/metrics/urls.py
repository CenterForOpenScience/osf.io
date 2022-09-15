from django.conf.urls import url

from . import views

app_name = 'osf'

urlpatterns = [
    url(r'^raw/(?P<url_path>[a-z0-9._/]*)$', views.RawMetricsView.as_view(), name=views.RawMetricsView.view_name),
    url(r'^preprints/views/$', views.PreprintViewMetrics.as_view(), name=views.PreprintViewMetrics.view_name),
    url(r'^preprints/downloads/$', views.PreprintDownloadMetrics.as_view(), name=views.PreprintDownloadMetrics.view_name),
    url(r'^registries_moderation/transitions/$', views.RegistriesModerationMetricsView.as_view(), name=views.RegistriesModerationMetricsView.view_name),

    url(
        r'^reports/$',
        views.ReportNameList.as_view(),
        name=views.ReportNameList.view_name,
    ),
    url(
        r'^reports/(?P<report_name>[a-z0-9_]+)/recent/$',
        views.RecentReportList.as_view(),
        name=views.RecentReportList.view_name,
    ),
    url(
        r'^events/counted_usage/$',
        views.CountedUsageView.as_view(),
        name=views.CountedUsageView.view_name,
    ),
    url(
        r'^query/node_analytics/(?P<node_guid>[a-z0-9]+)/(?P<timespan>week|fortnight|month)/$',
        views.NodeAnalyticsQuery.as_view(),
        name=views.NodeAnalyticsQuery.view_name,
    ),
]
