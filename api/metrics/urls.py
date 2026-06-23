from django.urls import re_path, path

from . import views

app_name = 'osf'

urlpatterns = [
    path('raw-<djelme_backend_name>/', views.RawMetricsView.as_view(), name=views.RawMetricsView.view_name, kwargs={'url_path': ''}),
    path('raw-<djelme_backend_name>/<path:url_path>', views.RawMetricsView.as_view(), name=views.RawMetricsView.view_name),
    re_path(r'^registries_moderation/transitions/$', views.RegistriesModerationMetricsView.as_view(), name=views.RegistriesModerationMetricsView.view_name),

    re_path(
        r'^reports/$',
        views.ReportNameList.as_view(),
        name=views.ReportNameList.view_name,
    ),
    path(
        'reports/<report_name>/',
        views.ReportList.as_view(),
        name=views.ReportList.view_name,
    ),
    path(
        'reports/<report_name>/recent/',
        views.RecentReportList.as_view(),
        name=views.RecentReportList.view_name,
    ),
    re_path(
        r'^events/counted_usage/$',
        views.CountedAuthUsageView.as_view(),
        name=views.CountedAuthUsageView.view_name,
    ),
    re_path(
        r'^query/node_analytics/(?P<node_guid>[a-z0-9]+)/(?P<timespan>week|fortnight|month)/$',
        views.NodeAnalyticsQuery.as_view(),
        name=views.NodeAnalyticsQuery.view_name,
    ),
    re_path(
        r'^query/user_visits/$',
        views.UserVisitsQuery.as_view(),
        name=views.UserVisitsQuery.view_name,
    ),
    re_path(
        r'^query/unique_user_visits/$',
        views.UniqueUserVisitsQuery.as_view(),
        name=views.UniqueUserVisitsQuery.view_name,
    ),
    path(
        'openapi.json',
        views.MetricsOpenapiView.as_view(),
        name=views.MetricsOpenapiView.view_name,
    ),
]
