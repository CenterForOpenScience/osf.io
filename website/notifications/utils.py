import collections


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
