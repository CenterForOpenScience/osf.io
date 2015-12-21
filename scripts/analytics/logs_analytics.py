from datetime import datetime as dt
from datetime import timedelta
import matplotlib.pyplot as plt

from modularodm import Q

from website.app import init_app
from website.models import NodeLog, User, Node

color_map = {
    'comments': 'red',
    'wiki': 'skyblue',
    'registrations': 'lime',
    'nodes': 'yellow',
    'files': 'magenta'
}

NUMBER_OF_DAY_DATA_POINTS = 30
NUMBER_OF_USERS_TO_SAMPLE = 1

def recent_time_frame(days=NUMBER_OF_DAY_DATA_POINTS):
    now = dt.utcnow()
    return [now - timedelta(days=i) for i in range(0, days)]

def build_time_query(end):
    return Q('date', 'gt', end - timedelta(days=1)) & Q('date', 'lt', end)

def order_users_get(sample_size=NUMBER_OF_USERS_TO_SAMPLE):
    print('Begin finding users.')
    users = list(User.find())
    for user in users:
        how_many = len(list(NodeLog.find(Q('user', 'eq', user))))
        if how_many < 1:
            users.remove(user)
    ordered = sorted(users, key=lambda x: x.get_activity_points(), reverse=True)
    print('Found users.')
    l = len(ordered)
    return ordered[int(l/50): int(l/50) + sample_size], ordered[int(l/40): int(l/40) + sample_size], ordered[int(l/30): int(l/30) + sample_size], ordered[int(l/20): int(l/20) + sample_size]

def get_agg_for_user(user, date):
    ret = {}
    nodes = list(Node.find(Q('contributors', 'contains', user._id)))
    for node in nodes:
        query_aggs = {
            'comments': len(list(NodeLog.find(Q('was_connected_to', 'eq', node) & Q('action', 'eq', NodeLog.COMMENT_ADDED) & build_time_query(date)))),
            'wiki': len(list(NodeLog.find(Q('was_connected_to', 'eq', node) & Q('action', 'eq', NodeLog.WIKI_UPDATED) & build_time_query(date)))),
            'registrations': len(list(NodeLog.find(Q('was_connected_to', 'eq', node) & Q('action', 'eq', NodeLog.PROJECT_REGISTERED) & build_time_query(date)))),
            'nodes': len(list(NodeLog.find(Q('was_connected_to', 'eq', node) & (Q('action', 'eq', NodeLog.PROJECT_CREATED) | Q('action', 'eq', NodeLog.NODE_CREATED)) & build_time_query(date)))),
            'files': len(list(NodeLog.find(Q('was_connected_to', 'eq', node) & (Q('action', 'eq', 'osf_storage_file_updated') | Q('action', 'eq', 'osf_storage_file_added')) & build_time_query(date)))),
        }
        ret.update({k: (ret.get(k) or 0 + v) for k, v in query_aggs.iteritems()})
    return ret

def main():
    top, mid, bot, bot2 = order_users_get()
    days_in_last_week = recent_time_frame()
    top_agg = {str(day): {} for day in days_in_last_week}
    mid_agg = {str(day): {} for day in days_in_last_week}
    bot_agg = {str(day): {} for day in days_in_last_week}
    bot2_agg = {str(day): {} for day in days_in_last_week}
    aggs = [(top, top_agg), (mid, mid_agg), (bot, bot_agg), (bot2, bot2_agg)]
    count = 0
    for sample, agg in aggs:
        for user in sample:
            for day in days_in_last_week:
                data = get_agg_for_user(user, day)
                agg.update(
                    {
                        str(day): {key: val + (agg[str(day)].get(key) or 0) for key, val in data.iteritems()}}
                )
                count += 1
                print('Log n aggregation: ' + str((count/float(NUMBER_OF_DAY_DATA_POINTS))*100) + '% Done')
        agg.update(
            {key: {k: v/float(len(sample)) for k, v in val.iteritems()} for key, val in agg.iteritems()}
        )
    days_map = top_agg.keys()
    days = range(1, len(days_in_last_week) + 1)
    plots = plt.subplots(4)[1]
    plots[0].set_ylabel('Number of events')
    plots[0].set_xlabel('Day of the week')
    plots[0].plot(
        days, [top_agg[day].get('comments') for day in days_map], color_map['comments'],
             days, [top_agg[day].get('wiki') for day in days_map], color_map['wiki'],
             days, [top_agg[day].get('registrations') for day in days_map], color_map['registrations'],
             days, [top_agg[day].get('nodes') for day in days_map], color_map['nodes'],
             days, [top_agg[day].get('files') for day in days_map], color_map['files'],
             )
    plots[1].set_ylabel('Number of events')
    plots[1].set_xlabel('Day of the week')
    plots[1].plot(
            days, [mid_agg[day].get('comments') for day in days_map], color_map['comments'],
             days, [mid_agg[day].get('wiki') for day in days_map], color_map['wiki'],
             days, [mid_agg[day].get('registrations') for day in days_map], color_map['registrations'],
             days, [mid_agg[day].get('nodes') for day in days_map], color_map['nodes'],
             days, [mid_agg[day].get('files') for day in days_map], color_map['files'],
             )
    plots[2].set_ylabel('Number of events')
    plots[2].set_xlabel('Day of the week')
    plots[2].plot(
            days, [bot_agg[day].get('comments') for day in days_map], color_map['comments'],
            days, [bot_agg[day].get('wiki') for day in days_map], color_map['wiki'],
            days, [bot_agg[day].get('registrations') for day in days_map], color_map['registrations'],
             days, [bot_agg[day].get('nodes') for day in days_map], color_map['nodes'],
            days, [bot_agg[day].get('files') for day in days_map], color_map['files'],
             )
    plots[3].set_ylabel('Number of events')
    plots[3].set_xlabel('Day of the week')
    plots[3].plot(
            days, [bot2_agg[day].get('comments') for day in days_map], color_map['comments'],
            days, [bot2_agg[day].get('wiki') for day in days_map], color_map['wiki'],
            days, [bot2_agg[day].get('registrations') for day in days_map], color_map['registrations'],
             days, [bot2_agg[day].get('nodes') for day in days_map], color_map['nodes'],
            days, [bot2_agg[day].get('files') for day in days_map], color_map['files'],
    )
    plt.show()


if __name__ == '__main__':
    init_app()
    main()
