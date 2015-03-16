import abc
import datetime
import json

import six


class OsfJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        else:
            return super(OsfJSONEncoder, self).default(obj)


@six.add_metaclass(abc.ABCMeta)
class OsfSerializer(object):


    def __init__(self, model):
        self.model = model

    @abc.abstractmethod
    def export(self):
        pass

    def export_as_json(self):
        return self._jsonify(self.export())

    _excluded_modm = [
        '__backrefs',
        '_version'
    ]

    def _jsonify(self, obj):
        return json.dumps(obj, cls=OsfJSONEncoder)

