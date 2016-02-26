from django.views.generic import ListView

from .models import OSFStatistic


class OSFStatisticsListView(ListView):
    model = OSFStatistic
