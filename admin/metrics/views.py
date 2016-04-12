from django.views.generic import ListView
from django.shortcuts import redirect
from django.shortcuts import render
from django.core.urlresolvers import reverse
from djqscsv import render_to_csv_response

from admin.metrics.models import OSFWebsiteStatistics
from admin.metrics.utils import get_osf_statistics


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
    # TODO: pass keen project id, read key and write key through context
    context = {}
    return render(request, 'metrics/sales_analytics.html', context)
