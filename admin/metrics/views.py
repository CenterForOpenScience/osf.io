from django.views.generic import ListView

from .models import OSFStatistic


class OSFStatisticsListView(ListView):
    model = OSFStatistic
    template_name = 'metrics/osf_statistics.html'
    context_object_name = 'metrics'
    paginate_by = 50
    paginate_orphans = 5
