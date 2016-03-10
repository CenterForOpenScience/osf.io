from django.views.generic import ListView
from django.shortcuts import redirect
from django.core.urlresolvers import reverse

from .models import OSFStatistic
from .utils import osf_site


def update_metrics(request):
    osf_site()
    return redirect(reverse('metrics:stats_list'))


class OSFStatisticsListView(ListView):
    model = OSFStatistic
    template_name = 'metrics/osf_statistics.html'
    context_object_name = 'metrics'
    paginate_by = 50
    paginate_orphans = 5
    ordering = '-date'
