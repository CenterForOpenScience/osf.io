import csv

from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.text import slugify
from django.views.generic import ListView

from admin.metrics.models import OSFWebsiteStatistics
from admin.metrics.utils import get_osf_statistics


def update_metrics(request):
    get_osf_statistics()
    return redirect(reverse('metrics:stats_list'))


def dump(qs, response):
    """
    source from http://palewi.re/posts/2009/03/03/django-recipe-dump-your-queryset-out-as-a-csv-file/

    Takes in a Django queryset and spits out a CSV file.

    Usage::

        >> from utils import dump2csv
        >> from dummy_app.models import *
        >> qs = DummyModel.objects.all()
        >> dump2csv.dump(qs, './data/dump.csv')

    Based on a snippet by zbyte64::

        http://www.djangosnippets.org/snippets/790/

    """
    model = qs.model
    writer = csv.writer(response)

    headers = []
    for field in model._meta.fields:
        headers.append(field.name)
    writer.writerow(headers)

    for obj in qs:
        row = []
        for field in headers:
            val = getattr(obj, field)
            if callable(val):
                val = val()
            if type(val) == unicode:
                val = val.encode('utf-8')
            row.append(val)
        writer.writerow(row)


def render_to_csv_response(queryset):
    filename = slugify(unicode(queryset.model.__name__)) + '_export.csv'

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=%s;' % filename
    response['Cache-Control'] = 'no-cache'

    dump(queryset, response)

    return response


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
