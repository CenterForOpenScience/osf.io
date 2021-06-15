from django.conf.urls import url

from api.outcome_report import views

app_name = "osf"

urlpatterns = [
    url(
        r"^$", views.OutcomeReportList.as_view(), name=views.OutcomeReportList.view_name
    ),
    url(
        r"^(?P<report_id>\w+)/$",
        views.OutcomeReportDetail.as_view(),
        name=views.OutcomeReportDetail.view_name,
    ),
]
