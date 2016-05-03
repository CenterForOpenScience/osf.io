from django.shortcuts import render
from django.shortcuts import redirect
from django.views.generic import ListView
from djqscsv import render_to_csv_response
from django.core.urlresolvers import reverse

from admin.metrics.utils import get_osf_statistics
from admin.metrics.models import OSFWebsiteStatistics
from admin.base.settings import KEEN_PROJECT_ID, KEEN_READ_KEY, ENTRY_POINTS
from bson.code import Code

from datetime import datetime, timedelta
from framework.mongo import database as db
from website.util.metrics import get_entry_point

def update_metrics(request):
    get_osf_statistics()
    return redirect(reverse('metrics:stats_list'))


def download_csv(request):
    queryset = OSFWebsiteStatistics.objects.all().order_by('-date')
    return render_to_csv_response(queryset)


def get_user_count(db=db, entry_points=ENTRY_POINTS):
    counts = []
    total = db.user.find({}).count()
    for i in entry_points:
        count = db.user.find({'system_tags': i}).count()
        percent = round(float(count) / float(total), 2)
        counts.append({'Product': i, 'Count': count, 'Percentage': percent})
    counts.append({'Product': 'osf', 'Count': total - sum([i['Count'] for i in counts]),
                  'Percentage': 1 - sum([i['Percentage'] for i in counts])})
    return {'items': counts}


def get_multi_product_metrics(db=db, timedelta=timedelta(days=365)):
    """
    Get the number of users using 2+ products within a period of time
    """
    start_date = datetime.now() - timedelta
    pipeline = [
        {'$match': {'date': {'$gt': start_date}}},
        {'$group': {'_id': '$user', 'node_id': {'$addToSet': '$params.node'}}}
    ]
    user_node = db.nodelog.aggregate(pipeline)['result']
    multi_product_count = 0
    for i in user_node:
        user_id = i['_id']
        node_id = i['node_id']
        product = []
        if user_id:
            entry_point = get_entry_point(db.user.find({'_id': user_id}).next()['system_tags'])
        nodes = db.node.find({'_id': {'$in': node_id}})
        for node in nodes:
            product.append(get_entry_point(node['system_tags']))
        if len(set(product)) > 1:
            multi_product_count += 1
    return {'multi_product_count': multi_product_count}


class OSFStatisticsListView(ListView):
    model = OSFWebsiteStatistics
    template_name = 'metrics/osf_statistics.html'
    context_object_name = 'metrics'
    paginate_by = 50
    paginate_orphans = 5
    ordering = '-date'


def sales_analytics(request):
    # TODO: pass keen project id, read key and write key through context

    # Compute metrics from OSF Database
    # User count for each product
    user_count = get_user_count(db, ENTRY_POINTS)
    multi_product_metrics_yearly = get_multi_product_metrics()
    multi_product_metrics_monthly = get_multi_product_metrics(timedelta=timedelta(days=30))

    context = {
        'keen_project_id': KEEN_PROJECT_ID,
        'keen_read_key': KEEN_READ_KEY,
        'user_count': user_count,
        'multi_product_metrics_yearly': multi_product_metrics_yearly,
        'multi_product_metrics_monthly': multi_product_metrics_monthly,
    }
    return render(request, 'metrics/sales_analytics.html', context)
