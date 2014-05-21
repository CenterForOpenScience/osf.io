from ..fields import Field


class DictionaryField(Field):

    data_type = dict
    mutable = True

    def __init__(self, *args, **kwargs):
        super(DictionaryField, self).__init__(*args, **kwargs)
        self._default = kwargs.get('default', {})
