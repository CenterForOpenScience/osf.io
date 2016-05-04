from admin.base.settings import KEEN_PROJECT_ID, KEEN_READ_KEY, ENTRY_POINTS
from admin.sales_analytics.utils import get_sorted_index
from datetime import datetime, timedelta
from framework.mongo import database as db
from website.util.metrics import get_entry_point


def get_user_count(db=db, entry_points=ENTRY_POINTS):
    """
    Get the number of users created from each entry point: osf, osf4m, prereg, and institution.
    """
    count_list = []
    percent_list = []
    tags = ['osf4m', 'prereg', 'institution', 'osf']
    total = db.user.find({}).count()
    for i in entry_points:
        count = db.user.find({'system_tags': i}).count()
        percent = round(float(count) / float(total), 2)
        count_list.append(count)
        percent_list.append(percent)
    osf_count = total - sum(count_list)
    osf_percent = 1 - sum(percent_list)
    count_list.append(osf_count)
    percent_list.append(osf_percent)
    sorted_index = get_sorted_index(count_list)
    count_list = [count_list[i] for i in sorted_index]
    percent_list = [percent_list[i] for i in sorted_index]
    tags = [tags[i] for i in sorted_index]

    return {'tags': tags, 'count': count_list, 'percent': percent_list, 'total': total}


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


def get_repeat_action_user_count(db=db, timedelta=timedelta(days=30)):
    """
    Get the number of users that have repetitive actions (with a 3 second difference)
    during the last month.
    """
    start_date = datetime.now() - timedelta
    pipeline = [
        {'$match': {'date': {'$gt': start_date}}},
        {'$group': {'_id': '$user', 'nodelog_id': {'$addToSet': '$_id'}}},
    ]

    user_nodelog = db.nodelog.aggregate(pipeline)['result']
    repeat_action_count = 0
    repeat_action_user_age = []
    for i in user_nodelog:
        if i['_id']:
            user_id = i['_id']
            nodelog_id = i['nodelog_id']
            nodelogs = db.nodelog.find({'_id': {'$in': nodelog_id}}).sort([('date', 1)])
            repeat_action_date = {}
            for nodelog in nodelogs:
                action = nodelog['action']
                date = nodelog['date']
                if action not in repeat_action_date:
                    repeat_action_date[action] = date
                elif abs((date - repeat_action_date[action]).total_seconds()) < 3:
                    repeat_action_date[action] = date
                else:
                    repeat_action_count += 1
                    date_registered = db.user.find({'_id': user_id}).next()['date_registered']
                    age = (date - date_registered).days
                    repeat_action_user_age.append(age)
                    break
    return {'repeat_action_count': repeat_action_count, 'repeat_action_age': repeat_action_user_age}


user_count = get_user_count(db, ENTRY_POINTS)
multi_product_metrics_yearly = get_multi_product_metrics()
multi_product_metrics_monthly = get_multi_product_metrics(timedelta=timedelta(days=30))
repeat_action_user_monthly = get_repeat_action_user_count()

