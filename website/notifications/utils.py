import collections
from website import settings


class NotificationsDict(dict):
    def __init__(self):
        super(dict, self).__init__()
        self.update(messages=[], children=collections.defaultdict(NotificationsDict))

    def add_message(self, keys, messages):
        d_to_use = self
        for key in keys:
            d_to_use = d_to_use['children'][key]
        if not isinstance(messages, list):
            messages = [messages]
        d_to_use['messages'].extend(messages)
        return True


class SubscriptionsDict(dict):
    def __init__(self):
        super(dict, self).__init__()
        self.update(subscriptions=collections.defaultdict(SubscriptionsDict),
                    children=collections.defaultdict(SubscriptionsDict))

    def add_subscription(self, keys, subscription):
        d_to_use = self
        for key in keys:
            d_to_use = d_to_use['children'][key]
        for notification_type in settings.NOTIFICATION_TYPES:
            if getattr(subscription, notification_type):
                d_to_use['subscriptions'] = {subscription.event_name: []}
                d_to_use['subscriptions'][subscription.event_name].append(notification_type)
        return True
