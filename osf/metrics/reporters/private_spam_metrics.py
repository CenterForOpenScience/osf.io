from osf.metrics.reports import PrivateSpamMetricsReport
from osf.external.oopspam.client import OOPSpamClient
from osf.external.askismet.client import AkismetClient
from ._base import MonthlyReporter
from osf.metrics.es8_metrics import PrivateSpamMetricsReportEs8


class PrivateSpamMetricsReporter(MonthlyReporter):
    report_name = 'Private Spam Metrics'

    def report(self):
        target_month = self.yearmonth.month_start()
        next_month = self.yearmonth.month_end()

        oopspam_client = OOPSpamClient()
        akismet_client = AkismetClient()

        reports = []

        report_es8 = PrivateSpamMetricsReportEs8(
            cycle_coverage=f"{self.yearmonth.year}.{self.yearmonth.month}",
            report_yearmonth=str(self.yearmonth),
            node_oopspam_flagged=oopspam_client.get_flagged_count(target_month, next_month, category='node'),
            node_oopspam_hammed=oopspam_client.get_hammed_count(target_month, next_month, category='node'),
            node_akismet_flagged=akismet_client.get_flagged_count(target_month, next_month, category='node'),
            node_akismet_hammed=akismet_client.get_hammed_count(target_month, next_month, category='node'),
            preprint_oopspam_flagged=oopspam_client.get_flagged_count(target_month, next_month, category='preprint'),
            preprint_oopspam_hammed=oopspam_client.get_hammed_count(target_month, next_month, category='preprint'),
            preprint_akismet_flagged=akismet_client.get_flagged_count(target_month, next_month, category='preprint'),
            preprint_akismet_hammed=akismet_client.get_hammed_count(target_month, next_month, category='preprint')
        )
        reports.append(report_es8)

        report = PrivateSpamMetricsReport(
            report_yearmonth=str(self.yearmonth),
            node_oopspam_flagged=report_es8.node_oopspam_flagged,
            node_oopspam_hammed=report_es8.node_oopspam_hammed,
            node_akismet_flagged=report_es8.node_akismet_flagged,
            node_akismet_hammed=report_es8.node_akismet_hammed,
            preprint_oopspam_flagged=report_es8.preprint_oopspam_flagged,
            preprint_oopspam_hammed=report_es8.preprint_oopspam_hammed,
            preprint_akismet_flagged=report_es8.preprint_akismet_flagged,
            preprint_akismet_hammed=report_es8.preprint_akismet_hammed,
        )
        reports.append(report)

        return reports
