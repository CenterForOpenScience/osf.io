# -*- coding: utf-8 -*-
'''Serializers for the project-related models.'''

import logging
from marshmallow import Serializer, fields
import hashlib

from framework.auth.model import User
from website.project.model import NodeLog
from website.project import clean_template_name


class UserSerializer(Serializer):
    id = fields.String(attribute="_primary_key", default='')
    url = fields.String(default='')
    username = fields.String(default='')
    fullname = fields.String(default='')
    registered = fields.Boolean(attribute="is_registered")
    gravatar = fields.Url(attribute="gravatar_url")


class UnregUserSerializer(Serializer):
    '''Serializer for an unregistered user.'''
    id = fields.Function(lambda user: hashlib.md5(user['nr_email']).hexdigest())
    fullname = fields.String(attribute="nr_name")
    registered = fields.Boolean(attribute="is_registered")


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
    category = fields.String(attribute='project_or_component')
    description = fields.String()
    api_url = fields.Url(relative=True)
    is_public = fields.Boolean()
    date_created = fields.DateTime()
    date_modified = fields.DateTime()
    is_fork = fields.Boolean()
    tags = fields.List(fields.String, default=[], attribute="tag_keys")
    children = fields.Boolean(attribute="nodes")  # Whether or not the node has children
    is_registration = fields.Boolean()
    registered_from_url = fields.Method("get_registered_from_url")
    registered_date = fields.Method("get_registered_date")
    registered_meta = fields.Method("get_registered_meta")
    registration_count = fields.Integer()
    parent = fields.Nested(ParentSerializer, attribute="parent_node")
    forked_from_url = fields.Method("get_forked_from_url")
    forked_date = fields.DateTime(default='')
    fork_count = fields.Function(lambda node: len(node.fork_list))
    watched_count = fields.Function(lambda node: len(node.watchconfig__watched))

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

    def get_forked_from_url(self, obj):
        return obj.forked_from.url if obj.is_fork else ''


class LogSerializer(Serializer):
    '''Serializer for NodeLogs.'''

    id = fields.String(attribute="_primary_key")
    user = fields.Nested(UserSerializer,
                        only=("id", "fullname", "registered", "url"))
    node = fields.Nested(BaseNodeSerializer, only=("id", 'category', "url", "api_url", "title"))
    action = fields.String()
    params = fields.Raw()
    date = fields.DateTime()
    contributors = fields.Method("get_contributors")
    contributor = fields.Method("get_contributor")
    api_key = fields.Function(lambda log: log.api_key.label if log.api_key else '')

    def get_contributor(self, obj):
        return self._render_log_contributor(obj.params.get("contributor", {}))

    def get_contributors(self, obj):
        return [self._render_log_contributor(c) for c in obj.params.get("contributors", [])]

    def _render_log_contributor(self, contributor):
        if isinstance(contributor, dict):
            rv = contributor.copy()
            rv.update({'registered' : False})
            return rv
        user = User.load(contributor)
        return UserSerializer(user).data


class NodeSerializer(BaseNodeSerializer):
    '''The Node Serializer. Gets all fields from BaseNodeSerializer
    and adds the recent logs.
    '''
    logs = fields.Method("get_recent_logs")

    def get_recent_logs(self, node):
        return LogSerializer(node.get_recent_logs(n=10)).data
