from osf.metrics.reports import PrivateSpamMetricsReport
from osf.external.oopspam.client import OOPSpamClient
from osf.external.askismet.client import AkismetClient
from ._base import MonthlyReporter

class PrivateSpamMetricsReporter(MonthlyReporter):
    report_name = 'Private Spam Metrics'

    def report(self):
        target_month = self.yearmonth.target_month()
        next_month = self.yearmonth.next_month()

        oopspam_client = OOPSpamClient()
        akismet_client = AkismetClient()

        report = PrivateSpamMetricsReport(
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

        return [report]
