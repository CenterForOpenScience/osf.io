from admin.base.settings import KEEN_PROJECT_ID, KEEN_READ_KEY, ENTRY_POINTS

from datetime import datetime, timedelta
from framework.mongo import database as db
from website.util.metrics import get_entry_point


def get_user_count(db=db, entry_points=ENTRY_POINTS):
    """
    Get the number of users created from each entry point: osf, osf4m, prereg, and institution.
    """
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
        {'$group': {'_id': '$user', 'node_id': {'$addToSet': '$params.node'},
                    'action': {'$addToSet': '$action'}}}
    ]
    user_node = db.nodelog.aggregate(pipeline)['result']
    multi_product_count = 0
    cross_product_count = 0
    multi_action_count = 0
    for i in user_node:
        if i['_id']:
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

            # Cross product count
            user = db.user.find_one({'_id': user_id})
            user_entry_point = get_entry_point(user['system_tags'])
            for j in product:
                if user_entry_point == product:
                    cross_product_count += 1

            # Action type
            if len(set(i['action'])) > 1:
                multi_action_count += 1

    return {'multi_product_count': multi_product_count,
            'cross_product_count': cross_product_count,
            'multi_action_count': multi_action_count,
            }


user_count = get_user_count(db, ENTRY_POINTS)
multi_product_metrics_yearly = get_multi_product_metrics()
multi_product_metrics_monthly = get_multi_product_metrics(timedelta=timedelta(days=30))
