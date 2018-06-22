from django.contrib.postgres.fields import JSONField
from django.db.models import Func, Value


class JSONBuildObject(Func):
    function = 'JSON_BUILD_OBJECT'
    output_field = JSONField()

    def __init__(self, **kwargs):
        args = []
        for key, value in kwargs.items():
            args.append(Value(key))
            args.append(value)

        super(JSONBuildObject, self).__init__(*args)


class ArrayAgg(Func):
    function = 'ARRAY_AGG'
    template = '%(function)s(%(expressions)s)'

    def convert_value(self, value, expression, connection, context=None):
        if not value:
            return []
        return value


class JSONAgg(ArrayAgg):
    function = 'JSON_AGG'
    template = '%(function)s(%(expressions)s%(order_by)s)'

    def __init__(self, *args, **kwargs):
        self._order_by = kwargs.pop('order_by', None)
        super(JSONAgg, self).__init__(*args, output_field=JSONField(), **kwargs)

    def as_sql(self, compiler, connection, function=None, template=None):
        if self._order_by:
            self.extra['order_by'] = ' ORDER BY ' + compiler.compile(self._order_by.resolve_expression(compiler.query))[0]
        else:
            self.extra['order_by'] = ''

        return super(JSONAgg, self).as_sql(compiler, connection, function=function, template=template)

    def as_sqlite(self, compiler, connection, **extra_context):
        return self.as_sql(compiler, connection, function='JSON_GROUP_ARRAY', **extra_context)
