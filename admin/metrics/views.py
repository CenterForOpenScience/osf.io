import datetime
from django.views.generic import TemplateView
from django.contrib.auth.mixins import PermissionRequiredMixin

from admin.base.settings import KEEN_CREDENTIALS


class MetricsView(PermissionRequiredMixin, TemplateView):
    template_name = 'metrics/osf_metrics.html'
    permission_required = 'osf.view_metrics'
    raise_exception = True

    def get_context_data(self, **kwargs):

        kwargs.update(KEEN_CREDENTIALS.copy())
        return super(MetricsView, self).get_context_data(**kwargs)


class FileDownloadCounts(TemplateView):
    template_name = 'metrics/osf_metrics.html'
    number_downloads_total = 0
    number_downloads_unique = 0
    update_date = datetime.datetime(2018, 1, 1, 0, 0)

    @classmethod
    def set_download_counts(cls, number_downloads_total, number_downloads_unique, update_date):
        if cls.number_downloads_total > number_downloads_total:
            raise ValueError('The imported total download counts is not correct.')
        if cls.number_downloads_unique > number_downloads_unique:
            raise ValueError('The imported unique download counts is not correct.')
        if update_date > update_date:
            raise ValueError('The update_date is not correct.')
        cls.number_downloads_total = number_downloads_total
        cls.number_downloads_unique = number_downloads_unique
        cls.update_date = update_date

    @classmethod
    def update(cls, number_downloads_total, number_downloads_unique, update_date):
        if update_date > update_date:
            raise ValueError('The download counts has been recently updated on {}.'.format(self.update_date))
        cls.number_downloads_total = number_downloads_total
        cls.number_downloads_unique = number_downloads_unique
        cls.update_date = update_date
