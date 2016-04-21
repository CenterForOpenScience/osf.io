from django.shortcuts import render
from django.shortcuts import redirect
from django.views.generic import ListView
from djqscsv import render_to_csv_response
from django.core.urlresolvers import reverse

from admin.metrics.utils import get_osf_statistics
from admin.metrics.models import OSFWebsiteStatistics
from admin.base.settings import KEEN_PROJECT_ID, KEEN_READ_KEY


def update_metrics(request):
    get_osf_statistics()
    return redirect(reverse('metrics:stats_list'))


def download_csv(request):
    queryset = OSFWebsiteStatistics.objects.all().order_by('-date')
    return render_to_csv_response(queryset)


class OSFStatisticsListView(ListView):
    model = OSFWebsiteStatistics
    template_name = 'metrics/osf_statistics.html'
    context_object_name = 'metrics'
    paginate_by = 50
    paginate_orphans = 5
    ordering = '-date'


def sales_analytics(request):
    context = {
        'keen_project_id': KEEN_PROJECT_ID,
        'keen_read_key': KEEN_READ_KEY
    }
    return render(request, 'metrics/sales_analytics.html', context)
