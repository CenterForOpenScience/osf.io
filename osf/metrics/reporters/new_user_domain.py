import logging
from collections import Counter

from osf.models import OSFUser
from osf.metrics.reports import NewUserDomainReport
from ._base import DailyReporter

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class NewUserDomainReporter(DailyReporter):
    def report(self, date):
        new_user_emails = OSFUser.objects.filter(
            date_confirmed__date=date,
            username__isnull=False,
        ).values_list('username', flat=True)

        domain_names = Counter(
            email.split('@')[-1]
            for email in new_user_emails
        )
        return [
            NewUserDomainReport(
                report_date=date,
                domain_name=domain_name,
                new_user_count=count,
            )
            for domain_name, count in domain_names.items()
        ]
