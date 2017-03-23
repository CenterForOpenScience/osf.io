from collections import OrderedDict

import ciso8601
import psycopg2
import ujson

from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.db.models.expressions import Func
from django.db.models.expressions import RawSQL
from django.db.models.query import ModelIterable


def _load(s):
    if s == '{}':
        return {}
    return ujson.loads(s)
psycopg2.extras.register_default_json(globally=True, loads=_load)


class JSONBuildArray(Func):
    function = 'JSON_BUILD_ARRAY'

    def __init__(self, *args, **kwargs):
        super(JSONBuildArray, self).__init__(*args, output_field=JSONField(), **kwargs)


class JSONAgg(ArrayAgg):
    function = 'JSON_AGG'
    template = '%(function)s(%(expressions)s%(order_by)s)'

    def __init__(self, *args, **kwargs):
        super(JSONAgg, self).__init__(*args, output_field=JSONField(), **kwargs)

    def as_sql(self, compiler, connection, function=None, template=None):
        if self.extra.get('order_by'):
            self.extra['order_by'] = ' ORDER BY ' + ', '.join(compiler.compile(x)[0] for x in self.extra['order_by'])
        else:
            self.extra['order_by'] = ''
        return super(JSONAgg, self).as_sql(compiler, connection, function=None, template=None)


class IncludeModelIterable(ModelIterable):

    @classmethod
    def parse_nested(cls, instance, field, nested, datas):
        if field.many_to_one:
            datas = (datas, )
        ps = []

        dts = [i for i, f in enumerate(field.related_model._meta.concrete_fields) if isinstance(f, models.DateTimeField)]

        for data in datas or []:
            data, nested_data = data[:-len(nested) or None], data[-len(nested):]

            for i in dts:
                if data[i]:
                    data[i] = ciso8601.parse_datetime(data[i])

            parsed = field.related_model.from_db(instance._state.db, None, data)

            for (f, n), d in zip(nested.items(), nested_data):
                cls.parse_nested(parsed, f, n, d)

            if field.remote_field.concrete:
                setattr(parsed, field.remote_field.get_cache_name(), instance)
            # import ipdb; ipdb.set_trace()

            ps.append(parsed)

        if field.many_to_one:
            return setattr(instance, field.get_cache_name(), ps[0])

        if not hasattr(instance, '_prefetched_objects_cache'):
            instance._prefetched_objects_cache = {}
        instance._prefetched_objects_cache[field.name] = field.related_model.objects.none()
        instance._prefetched_objects_cache[field.name]._result_cache = ps

    @classmethod
    def parse_includes(cls, instance, fields):
        for field, nested in fields.items():
            data = getattr(instance, '__' + field.name)
            delattr(instance, '__' + field.name)
            cls.parse_nested(instance, field, nested, data)

    def __iter__(self):
        for instance in super(IncludeModelIterable, self).__iter__():
            self.parse_includes(instance, self.queryset._includes)

            yield instance


class IncludeQuerySet(models.QuerySet):

    def __init__(self, *args, **kwargs):
        super(IncludeQuerySet, self).__init__(*args, **kwargs)
        self._include_limit = None
        self._includes = OrderedDict()
        self._iterable_class = IncludeModelIterable

    def include(self, *related_names, **kwargs):
        clone = self._clone()
        clone._include_limit = kwargs.pop('limit_includes', None)
        assert not kwargs, '"limit_includes" is the only accepted kwargs. Eat your heart out 2.7'

        for name in related_names:
            ctx, model = self._includes, self.model
            for spl in name.split('__'):
                field = model._meta.get_field(spl)
                model = field.related_model
                ctx = ctx.setdefault(field, OrderedDict())

        for field in self._includes.keys():
            clone._include(field)

        return clone

    def _clone(self):
        clone = super(IncludeQuerySet, self)._clone()
        clone._includes = self._includes
        return clone

    def _include(self, field):
        self.query.get_initial_alias()
        sql, params = self._build_include_sql(field, self._includes[field], self.query)
        # Use add_extra to avoid a pointless call to _clone
        # For some reason it doesn't take keywords...
        self.query.add_extra({'__' + field.name: sql}, params, None, None, None, None)

    def _build_include_sql(self, field, children, host_query):
        host_model = field.model
        model = field.related_model

        # join_columns on generic relations are backwards
        # Probably a reason/ better way to handle this
        if isinstance(field, GenericRelation):
            column, host_column = field.get_joining_columns()[0]
        else:
            host_column, column = field.get_joining_columns()[0]

        qs = model.objects.all()

        # TODO be able to set limits per thing included
        if self._include_limit:
            qs.query.set_limits(0, self._include_limit)

        qs.query.get_initial_alias()
        qs.query.bump_prefix(host_query)

        table = qs.query.get_compiler(using=self.db).quote_name_unless_alias(qs.query.get_initial_alias())
        host_table = host_query.get_compiler(using=self.db).quote_name_unless_alias(host_query.get_initial_alias())

        kwargs = {}
        if qs.ordered:
            kwargs['order_by'] = zip(*qs.query.get_compiler(using=self.db).get_order_by())[0]

        where = ['{table}."{column}" = {host_table}."{host_column}"'.format(
            table=table,
            column=column,
            host_table=host_table,
            host_column=host_column,
        )]

        if isinstance(field, GenericRelation):
            where.append('{table}."{content_type}" = {content_type_id}'.format(
                table=table,
                content_type=model._meta.get_field(field.content_type_field_name).column,
                content_type_id=ContentType.objects.get_for_model(host_model).pk
            ))

        qs.query.add_extra(None, None, where, None, None, None)

        expressions = [f.column for f in model._meta.concrete_fields]

        for item in children.items():
            item = item + (qs.query, )
            expressions.append(RawSQL(*self._build_include_sql(*item)))

        agg = JSONBuildArray(*expressions)

        # many_to_one is a bit of a misnomer, the field we have is the "one" side
        if not field.many_to_one:
            agg = JSONAgg(agg, **kwargs)

        qs.query.add_annotation(agg, '__fields', is_summary=True)

        qs = qs.values_list('__fields')
        qs.query.clear_ordering(True)

        return qs.query.sql_with_params()


# IncludeQuerySet.as_manager().contribute_to_class(Guid, 'bobjects')
# IncludeQuerySet.as_manager().contribute_to_class(AbstractNode, 'bobjects')
# IncludeQuerySet.as_manager().contribute_to_class(Contributor, 'bobjects')
# IncludeQuerySet.as_manager().contribute_to_class(OSFUser, 'bobjects')
