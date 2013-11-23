# -*- coding: utf-8 -*-
'''Serializers for the project-related models.'''

from marshmallow import Serializer, fields

from framework.auth.model import User
from website.project.model import NodeLog
from website.project import clean_template_name


class UserSerializer(Serializer):
    id = fields.String(attribute="_primary_key", default='')
    url = fields.String(default='')
    username = fields.String(default='')
    fullname = fields.String(default='')
    registered = fields.Boolean(attribute="is_registered")


class NodeCategory(fields.Raw):
    '''Custom field that has value 'project' if a node's category is a project,
    'component' otherwise.
    '''
    def format(self, value):
        return 'project' if value == 'project' else 'component'

DATE_FORMAT = '%Y/%m/%d %I:%M %p'


class NodeDateTime(fields.Raw):
    def format(self, value):
        return value.strftime(DATE_FORMAT)

class ParentSerializer(Serializer):
    '''Serializer for node's parent.'''
    id = fields.String(attribute="_primary_key")
    url = fields.Url(relative=True)
    api_url = fields.Url(relative=True)
    title = fields.String()


class BaseNodeSerializer(Serializer):
    id = fields.String(attribute="_primary_key")
    url = fields.Url(relative=True)
    title = fields.String()
    category = NodeCategory()
    description = fields.String()
    api_url = fields.Url(relative=True)
    is_public = fields.Boolean()
    date_created = NodeDateTime()
    date_modified = NodeDateTime()
    is_fork = fields.Boolean()
    tags = fields.List(fields.String, attribute="tag_keys")
    children = fields.Boolean(attribute="nodes")  # Whether or not the node has children
    is_registration = fields.Boolean()
    registered_from_url = fields.Method("get_registered_from_url")
    registered_date = fields.Method("get_registered_date")
    registered_meta = fields.Method("get_registered_meta")
    registration_count = fields.Integer()
    parent = fields.Nested(ParentSerializer, attribute="parent_node")
    forked_from_url = fields.Method("get_forked_from_url")
    forked_date = fields.DateTime(default='')
    fork_count = fields.Method("get_fork_count")
    watched_count = fields.Method("get_watched_count")

    def get_registered_from_url(self, obj):
        return obj.registered_from.url if obj.is_registration else ''

    def get_registered_date(self, obj):
        return obj.project.registered_date.strftime(DATE_FORMAT) \
                if obj.is_registration else ''

    def get_registered_meta(self, obj):
        return  [
            {
                'name_no_ext': meta.replace('.txt', ''),
                'name_clean': clean_template_name(meta),
            }
            for meta in obj.registered_meta or []
        ]

    def get_watched_count(self, obj):
        return len(obj.watchconfig__watched)

    def get_forked_from_url(self, obj):
        return obj.forked_from.url if obj.is_fork else ''

    def get_fork_count(self, obj):
        return len(obj.fork_list)


class LogSerializer(Serializer):
    '''Serializer for NodeLogs.'''

    id = fields.String(attribute="_primary_key")
    user = fields.Nested(UserSerializer,
                        only=("id", "fullname", "registered", "url"))
    node = fields.Nested(BaseNodeSerializer, only=("id", "url", "api_url", "title"))
    category = fields.Method("get_category")
    action = fields.String()
    params = fields.Raw()
    date = fields.DateTime()
    contributors = fields.Method("get_contributors")
    contributor = fields.Method("get_contributor")
    api_key = fields.Function(lambda log: log.api_key.label if log.api_key else '')

    def get_category(self, obj):
        if obj.node:
            return 'project' if obj.node.category == 'project' else 'component'
        else:
            return ''

    def get_contributor(self, obj):
        return self._render_log_contributor(obj.params.get("contributor", {}))

    def get_contributors(self, obj):
        return [self._render_log_contributor(c) for c in obj.params.get("contributors", [])]

    # TODO: make this its own serializer?
    def _render_log_contributor(self, contributor):
        if isinstance(contributor, dict):
            rv = contributor.copy()
            rv.update({'registered' : False})
            return rv
        user = User.load(contributor)
        return {
            'id' : user._primary_key,
            'fullname' : user.fullname,
            'registered' : True,
        }

class NodeSerializer(BaseNodeSerializer):
    '''The Node Serializer. Gets all fields from BaseNodeSerializer
    and adds the recent logs.
    '''
    logs = fields.Method("get_recent_logs")

    def get_recent_logs(self, node):
        return [LogSerializer(log).data for log in node.get_recent_logs(n=10)]
