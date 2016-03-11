from django.views.generic import ListView
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from djqscsv import render_to_csv_response

from .models import OSFStatistic
from .utils import get_osf_statistics


def update_metrics(request):
    get_osf_statistics()
    return redirect(reverse('metrics:stats_list'))


def download_csv(request):
    queryset = OSFStatistic.objects.all()
    return render_to_csv_response(queryset)


class OSFStatisticsListView(ListView):
    model = OSFStatistic
    template_name = 'metrics/osf_statistics.html'
    context_object_name = 'metrics'
    paginate_by = 50
    paginate_orphans = 5
    ordering = '-date'
