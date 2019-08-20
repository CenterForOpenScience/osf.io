# -*- coding: utf-8 -*-
from flask import request

from .provider import ZoteroCitationsProvider
from website.citations.views import GenericCitationViews
from website.project.decorators import (
    must_have_addon, must_be_addon_authorizer,
    must_have_permission, must_not_be_registration,
    must_be_contributor_or_public
)
from api.base.utils import is_truthy
from osf.utils.permissions import WRITE


class ZoteroViews(GenericCitationViews):
    def set_config(self):
        addon_short_name = self.addon_short_name
        Provider = self.Provider

        @must_not_be_registration
        @must_have_addon(addon_short_name, 'user')
        @must_have_addon(addon_short_name, 'node')
        @must_be_addon_authorizer(addon_short_name)
        @must_have_permission(WRITE)
        def _set_config(node_addon, user_addon, auth, **kwargs):
            """ Changes folder associated with addon.
            Returns serialized node settings
            """
            provider = Provider()
            args = request.get_json()
            external_list_id = args.get('external_list_id')
            external_list_name = args.get('external_list_name')
            external_library_id = args.get('external_library_id', None)
            external_library_name = args.get('external_library_name', None)
            provider.set_config(
                node_addon,
                auth.user,
                external_list_id,
                external_list_name,
                auth,
                external_library_id,
                external_library_name
            )
            return {
                'result': provider.serializer(
                    node_settings=node_addon,
                    user_settings=auth.user.get_addon(addon_short_name),
                ).serialized_node_settings
            }
        _set_config.__name__ = '{0}_set_config'.format(addon_short_name)
        return _set_config

    def library_list(self):
        addon_short_name = self.addon_short_name

        @must_be_contributor_or_public
        @must_have_addon(addon_short_name, 'node')
        def _library_list(auth, node_addon, **kwargs):
            """ Returns a list of group libraries - for use with Zotero addon
            """
            limit = request.args.get('limit')
            start = request.args.get('start')
            return_count = is_truthy(request.args.get('return_count', False))
            append_personal = is_truthy(request.args.get('append_personal', True))
            return node_addon.get_folders(limit=limit, start=start, return_count=return_count, append_personal=append_personal)
        _library_list.__name__ = '{0}_library_list'.format(addon_short_name)
        return _library_list

zotero_views = ZoteroViews('zotero', ZoteroCitationsProvider)
