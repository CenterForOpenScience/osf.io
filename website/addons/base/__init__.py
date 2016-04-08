# -*- coding: utf-8 -*-
import os
import glob
import importlib
import mimetypes
from bson import ObjectId
from modularodm import fields
from mako.lookup import TemplateLookup
from time import sleep

import requests
from modularodm import Q

from framework.auth.decorators import must_be_logged_in
from framework.mongo import StoredObject
from framework.routing import process_rules
from framework.exceptions import (
    PermissionsError,
    HTTPError,
)
from framework.auth import Auth

from website import settings
from website.addons.base import serializer, logger
from website.project.model import Node, User
from website.util import waterbutler_url_for

from website.oauth.signals import oauth_complete

NODE_SETTINGS_TEMPLATE_DEFAULT = os.path.join(
    settings.TEMPLATES_PATH,
    'project',
    'addon',
    'node_settings_default.mako',
)

USER_SETTINGS_TEMPLATE_DEFAULT = os.path.join(
    settings.TEMPLATES_PATH,
    'profile',
    'user_settings_default.mako',
)

lookup = TemplateLookup(
    directories=[
        settings.TEMPLATES_PATH
    ]
)


def _is_image(filename):
    mtype, _ = mimetypes.guess_type(filename)
    return mtype and mtype.startswith('image')


class AddonConfig(object):

    def __init__(self, short_name, full_name, owners, categories,
                 added_default=None, added_mandatory=None,
                 node_settings_model=None, user_settings_model=None, include_js=None, include_css=None,
                 widget_help=None, views=None, configs=None, models=None,
                 has_hgrid_files=False, get_hgrid_data=None, max_file_size=None, high_max_file_size=None,
                 accept_extensions=True,
                 node_settings_template=None, user_settings_template=None,
                 **kwargs):

        self.models = models
        self.settings_models = {}

        if node_settings_model:
            node_settings_model.config = self
            self.settings_models['node'] = node_settings_model

        if user_settings_model:
            user_settings_model.config = self
            self.settings_models['user'] = user_settings_model

        self.short_name = short_name
        self.full_name = full_name
        self.owners = owners
        self.categories = categories

        self.added_default = added_default or []
        self.added_mandatory = added_mandatory or []
        if set(self.added_mandatory).difference(self.added_default):
            raise ValueError('All mandatory targets must also be defaults.')

        self.include_js = self._include_to_static(include_js or {})
        self.include_css = self._include_to_static(include_css or {})

        self.widget_help = widget_help

        self.views = views or []
        self.configs = configs or []

        self.has_hgrid_files = has_hgrid_files
        # WARNING: get_hgrid_data can return None if the addon is added but has no credentials.
        self.get_hgrid_data = get_hgrid_data  # if has_hgrid_files and not get_hgrid_data rubeus.make_dummy()
        self.max_file_size = max_file_size
        self.high_max_file_size = high_max_file_size
        self.accept_extensions = accept_extensions

        # Provide the path the the user_settings template
        self.user_settings_template = user_settings_template
        if not user_settings_template or not os.path.exists(os.path.dirname(user_settings_template)):
            # Use the default template (ATM for OAuth addons)
            self.user_settings_template = USER_SETTINGS_TEMPLATE_DEFAULT

        # Provide the path the the node_settings template
        self.node_settings_template = node_settings_template
        if not node_settings_template or not os.path.exists(os.path.dirname(node_settings_template)):
            # Use the default template
            self.node_settings_template = NODE_SETTINGS_TEMPLATE_DEFAULT

        # Build template lookup
        template_dirs = list(
            set(
                [
                    path
                    for path in [os.path.dirname(self.user_settings_template), os.path.dirname(self.node_settings_template), settings.TEMPLATES_PATH]
                    if os.path.exists(path)
                ]
            )
        )
        if template_dirs:
            self.template_lookup = TemplateLookup(
                directories=template_dirs
            )
        else:
            self.template_lookup = None

    def _static_url(self, filename):
        """Build static URL for file; use the current addon if relative path,
        else the global static directory.

        :param str filename: Local path to file
        :return str: Static URL for file

        """
        if filename.startswith('/'):
            return filename
        return '/static/addons/{addon}/{filename}'.format(
            addon=self.short_name,
            filename=filename,
        )

    def _include_to_static(self, include):
        """

        """
        # TODO: minify static assets
        return {
            key: [
                self._static_url(item)
                for item in value
            ]
            for key, value in include.iteritems()
        }

    # TODO: Make INCLUDE_JS and INCLUDE_CSS one option

    @property
    def icon(self):
        try:
            return self._icon
        except AttributeError:
            static_path = os.path.join('website', 'addons', self.short_name, 'static')
            static_files = glob.glob(os.path.join(static_path, 'comicon.*'))
            return next((
                os.path.split(filename)[1]
                for filename in static_files
                if _is_image(filename)),
                None
            )

    @property
    def icon_url(self):
        return self._static_url(self.icon) if self.icon else None

    def to_json(self):
        return {
            'short_name': self.short_name,
            'full_name': self.full_name,
            'capabilities': self.short_name in settings.ADDON_CAPABILITIES,
            'addon_capabilities': settings.ADDON_CAPABILITIES.get(self.short_name),
            'icon': self.icon_url,
            'has_page': 'page' in self.views,
            'has_widget': 'widget' in self.views,
        }

    @property
    def path(self):
        return os.path.join(settings.BASE_PATH, self.short_name)


class AddonSettingsBase(StoredObject):

    _id = fields.StringField(default=lambda: str(ObjectId()))
    deleted = fields.BooleanField(default=False)

    _meta = {
        'abstract': True,
    }

    def delete(self, save=True):
        self.deleted = True
        self.on_delete()
        if save:
            self.save()

    def undelete(self, save=True):
        self.deleted = False
        self.on_add()
        if save:
            self.save()

    def to_json(self, user):
        return {
            'addon_short_name': self.config.short_name,
            'addon_full_name': self.config.full_name,
        }

    #############
    # Callbacks #
    #############

    def on_add(self):
        """Called when the addon is added (or re-added) to the owner (User or Node)."""
        pass

    def on_delete(self):
        """Called when the addon is deleted from the owner (User or Node)."""
        pass


class AddonUserSettingsBase(AddonSettingsBase):

    owner = fields.ForeignField('user', backref='addons')

    _meta = {
        'abstract': True,
    }

    def __repr__(self):
        if self.owner:
            return '<{cls} owned by user {uid}>'.format(cls=self.__class__.__name__, uid=self.owner._id)
        else:
            return '<{cls} with no owner>'.format(cls=self.__class__.__name__)

    @property
    def public_id(self):
        return None

    @property
    def has_auth(self):
        """Whether the user has added credentials for this addon."""
        return False

    def get_backref_key(self, schema, backref_name):
        return schema._name + '__' + backref_name

    # TODO: Test me @asmacdo
    @property
    def nodes_authorized(self):
        """Get authorized, non-deleted nodes. Returns an empty list if the
        attached add-on does not include a node model.

        """
        try:
            schema = self.config.settings_models['node']
        except KeyError:
            return []
        nodes_backref = self.get_backref_key(schema, 'authorized')
        return [
            node_addon.owner
            for node_addon in getattr(self, nodes_backref)
            if node_addon.owner and not node_addon.owner.is_deleted
        ]

    @property
    def can_be_merged(self):
        return hasattr(self, 'merge')

    def to_json(self, user):
        ret = super(AddonUserSettingsBase, self).to_json(user)
        ret['has_auth'] = self.has_auth
        ret.update({
            'nodes': [
                {
                    '_id': node._id,
                    'url': node.url,
                    'title': node.title,
                    'registered': node.is_registration,
                    'api_url': node.api_url
                }
                for node in self.nodes_authorized
            ]
        })
        return ret


@oauth_complete.connect
def oauth_complete(provider, account, user):
    if not user or not account:
        return
    user.add_addon(account.provider)
    user.save()


class AddonOAuthUserSettingsBase(AddonUserSettingsBase):
    _meta = {
        'abstract': True,
    }

    # Keeps track of what nodes have been given permission to use external
    #   accounts belonging to the user.
    oauth_grants = fields.DictionaryField()
    # example:
    # {
    #     '<Node._id>': {
    #         '<ExternalAccount._id>': {
    #             <metadata>
    #         },
    #     }
    # }
    #
    # metadata here is the specific to each addon.

    # The existence of this property is used to determine whether or not
    #   an addon instance is an "OAuth addon" in
    #   AddonModelMixin.get_oauth_addons().
    oauth_provider = None

    serializer = serializer.OAuthAddonSerializer

    @property
    def has_auth(self):
        return bool(self.external_accounts)

    @property
    def external_accounts(self):
        """The user's list of ``ExternalAccount`` instances for this provider"""
        return [
            x for x in self.owner.external_accounts
            if x.provider == self.oauth_provider.short_name
        ]

    def delete(self, save=True):
        for account in self.external_accounts:
            self.revoke_oauth_access(account, save=False)
        super(AddonOAuthUserSettingsBase, self).delete(save=save)

    def grant_oauth_access(self, node, external_account, metadata=None):
        """Give a node permission to use an ``ExternalAccount`` instance."""
        # ensure the user owns the external_account
        if external_account not in self.owner.external_accounts:
            raise PermissionsError()

        metadata = metadata or {}

        # create an entry for the node, if necessary
        if node._id not in self.oauth_grants:
            self.oauth_grants[node._id] = {}

        # create an entry for the external account on the node, if necessary
        if external_account._id not in self.oauth_grants[node._id]:
            self.oauth_grants[node._id][external_account._id] = {}

        # update the metadata with the supplied values
        for key, value in metadata.iteritems():
            self.oauth_grants[node._id][external_account._id][key] = value

        self.save()

    @must_be_logged_in
    def revoke_oauth_access(self, external_account, auth, save=True):
        """Revoke all access to an ``ExternalAccount``.

        TODO: This should accept node and metadata params in the future, to
            allow fine-grained revocation of grants. That's not yet been needed,
            so it's not yet been implemented.
        """
        for node in self.get_nodes_with_oauth_grants(external_account):
            try:
                addon_settings = node.get_addon(external_account.provider, deleted=True)
            except AttributeError:
                # No associated addon settings despite oauth grant
                pass
            else:
                addon_settings.deauthorize(auth=auth)

        if User.find(Q('external_accounts', 'contains', external_account._id)).count() == 1:
            # Only this user is using the account, so revoke remote access as well.
            self.revoke_remote_oauth_access(external_account)

        for key in self.oauth_grants:
            self.oauth_grants[key].pop(external_account._id, None)
        if save:
            self.save()

    def revoke_remote_oauth_access(self, external_account):
        """ Makes outgoing request to remove the remote oauth grant
        stored by third-party provider.

        Individual addons must override this method, as it is addon-specific behavior.
        Not all addon providers support this through their API, but those that do
        should also handle the case where this is called with an external_account
        with invalid credentials, to prevent a user from being unable to disconnect
        an account.
        """
        pass

    def verify_oauth_access(self, node, external_account, metadata=None):
        """Verify that access has been previously granted.

        If metadata is not provided, this checks only if the node can access the
        account. This is suitable to check to see if the node's addon settings
        is still connected to an external account (i.e., the user hasn't revoked
        it in their user settings pane).

        If metadata is provided, this checks to see that all key/value pairs
        have been granted. This is suitable for checking access to a particular
        folder or other resource on an external provider.
        """

        metadata = metadata or {}

        # ensure the grant exists
        try:
            grants = self.oauth_grants[node._id][external_account._id]
        except KeyError:
            return False

        # Verify every key/value pair is in the grants dict
        for key, value in metadata.iteritems():
            if key not in grants or grants[key] != value:
                return False

        return True

    def get_nodes_with_oauth_grants(self, external_account):
        # Generator of nodes which have grants for this external account
        for node_id, grants in self.oauth_grants.iteritems():
            node = Node.load(node_id)
            if external_account._id in grants.keys() and not node.is_deleted:
                yield node

    def get_attached_nodes(self, external_account):
        for node in self.get_nodes_with_oauth_grants(external_account):
            if node is None:
                continue
            node_settings = node.get_addon(self.oauth_provider.short_name)

            if node_settings is None:
                continue

            if node_settings.external_account == external_account:
                yield node

    def merge(self, user_settings):
        """Merge `user_settings` into this instance"""
        if user_settings.__class__ is not self.__class__:
            raise TypeError('Cannot merge different addons')

        for node_id, data in user_settings.oauth_grants.iteritems():
            if node_id not in self.oauth_grants:
                self.oauth_grants[node_id] = data
            else:
                node_grants = user_settings.oauth_grants[node_id].iteritems()
                for ext_acct, meta in node_grants:
                    if ext_acct not in self.oauth_grants[node_id]:
                        self.oauth_grants[node_id][ext_acct] = meta
                    else:
                        for k, v in meta:
                            if k not in self.oauth_grants[node_id][ext_acct]:
                                self.oauth_grants[node_id][ext_acct][k] = v

        user_settings.oauth_grants = {}
        user_settings.save()

        try:
            config = settings.ADDONS_AVAILABLE_DICT[
                self.oauth_provider.short_name
            ]
            Model = config.settings_models['node']
        except KeyError:
            pass
        else:
            connected = Model.find(Q('user_settings', 'eq', user_settings))
            for node_settings in connected:
                node_settings.user_settings = self
                node_settings.save()

        self.save()

    def to_json(self, user):
        ret = super(AddonOAuthUserSettingsBase, self).to_json(user)

        ret['accounts'] = self.serializer(
            user_settings=self
        ).serialized_accounts

        return ret

    #############
    # Callbacks #
    #############

    def on_delete(self):
        """When the user deactivates the addon, clear auth for connected nodes.
        """
        super(AddonOAuthUserSettingsBase, self).on_delete()
        nodes = [Node.load(node_id) for node_id in self.oauth_grants.keys()]
        for node in nodes:
            node_addon = node.get_addon(self.oauth_provider.short_name)
            if node_addon and node_addon.user_settings == self:
                node_addon.clear_auth()

class AddonNodeSettingsBase(AddonSettingsBase):

    owner = fields.ForeignField('node', backref='addons')

    _meta = {
        'abstract': True,
    }

    @property
    def complete(self):
        """Whether or not this addon is properly configured
        :rtype bool:
        """
        raise NotImplementedError()

    @property
    def has_auth(self):
        """Whether the node has added credentials for this addon."""
        return False

    def to_json(self, user):
        ret = super(AddonNodeSettingsBase, self).to_json(user)
        ret.update({
            'user': {
                'permissions': self.owner.get_permissions(user)
            },
            'node': {
                'id': self.owner._id,
                'api_url': self.owner.api_url,
                'url': self.owner.url,
                'is_registration': self.owner.is_registration,
            },
            'node_settings_template': os.path.basename(self.config.node_settings_template),
        })
        return ret

    def render_config_error(self, data):
        """

        """
        # Note: `config` is added to `self` in `AddonConfig::__init__`.
        template = lookup.get_template('project/addon/config_error.mako')
        return template.get_def('config_error').render(
            title=self.config.full_name,
            name=self.config.short_name,
            **data
        )

    #############
    # Callbacks #
    #############

    def before_page_load(self, node, user):
        """

        :param User user:
        :param Node node:

        """
        pass

    def before_remove_contributor(self, node, removed):
        """
        :param Node node:
        :param User removed:
        """
        pass

    def after_remove_contributor(self, node, removed, auth=None):
        """
        :param Node node:
        :param User removed:
        """
        pass

    def before_make_public(self, node):
        """

        :param Node node:
        :returns: Alert message or None

        """
        pass

    def before_make_private(self, node):
        """

        :param Node node:
        :returns: Alert message or None

        """
        pass

    def after_set_privacy(self, node, permissions):
        """

        :param Node node:
        :param str permissions:

        """
        pass

    def before_fork(self, node, user):
        """Return warning text to display if user auth will be copied to a
        fork.
        :param Node node:
        :param Uder user
        :returns Alert message
        """

        if hasattr(self, "user_settings"):
            if self.user_settings is None:
                return (
                    u'Because you have not configured the authorization for this {addon} add-on, this '
                    u'{category} will not transfer your authentication to '
                    u'the forked {category}.'
                ).format(
                    addon=self.config.full_name,
                    category=node.project_or_component,
                )

            elif self.user_settings and self.user_settings.owner == user:
                return (
                    u'Because you have authorized the {addon} add-on for this '
                    u'{category}, forking it will also transfer your authentication to '
                    u'the forked {category}.'
                ).format(
                    addon=self.config.full_name,
                    category=node.project_or_component,
                )
            else:
                return (
                    u'Because the {addon} add-on has been authorized by a different '
                    u'user, forking it will not transfer authentication to the forked '
                    u'{category}.'
                ).format(
                    addon=self.config.full_name,
                    category=node.project_or_component,
                )

    def after_fork(self, node, fork, user, save=True):
        """

        :param Node node:
        :param Node fork:
        :param User user:
        :param bool save:
        :returns: Tuple of cloned settings and alert message

        """
        clone = self.clone()
        clone.owner = fork

        if save:
            clone.save()

        return clone, None

    def before_register(self, node, user):
        """

        :param Node node:
        :param User user:
        :returns: Alert message

        """
        pass

    def after_register(self, node, registration, user, save=True):
        """

        :param Node node:
        :param Node registration:
        :param User user:
        :param bool save:
        :returns: Tuple of cloned settings and alert message

        """
        return None, None

    def after_delete(self, node, user):
        """

        :param Node node:
        :param User user:

        """
        pass

############
# Archiver #
############
class GenericRootNode(object):
    path = '/'
    name = ''

class StorageAddonBase(object):
    """
    Mixin class for traversing file trees of addons with files
    """

    root_node = GenericRootNode()

    @property
    def archive_folder_name(self):
        name = "Archive of {addon}".format(addon=self.config.full_name)
        folder_name = getattr(self, 'folder_name', '').lstrip('/').strip()
        if folder_name:
            name = name + ": {folder}".format(folder=folder_name)
        return name

    def _get_fileobj_child_metadata(self, filenode, user, cookie=None, version=None):
        kwargs = dict(
            provider=self.config.short_name,
            path=filenode.get('path', ''),
            node=self.owner,
            user=user,
            view_only=True,
        )
        if cookie:
            kwargs['cookie'] = cookie
        if version:
            kwargs['version'] = version
        metadata_url = waterbutler_url_for(
            'metadata',
            **kwargs
        )
        res = requests.get(metadata_url)
        if res.status_code != 200:
            raise HTTPError(res.status_code, data={
                'error': res.json(),
            })
        # TODO: better throttling?
        sleep(1.0 / 5.0)
        return res.json().get('data', [])

    def _get_file_tree(self, filenode=None, user=None, cookie=None, version=None):
        """
        Recursively get file metadata
        """
        filenode = filenode or {
            'path': '/',
            'kind': 'folder',
            'name': self.root_node.name,
        }
        if filenode.get('kind') == 'file':
            return filenode
        elif 'size' in filenode:
            return filenode
        kwargs = {
            'version': version,
            'cookie': cookie,
        }
        filenode['children'] = [
            self._get_file_tree(child, user, cookie=cookie)
            for child in self._get_fileobj_child_metadata(filenode, user, **kwargs)
        ]
        return filenode

class AddonOAuthNodeSettingsBase(AddonNodeSettingsBase):
    _meta = {
        'abstract': True,
    }

    # TODO: Validate this field to be sure it matches the provider's short_name
    # NOTE: Do not set this field directly. Use ``set_auth()``
    external_account = fields.ForeignField('externalaccount',
                                           backref='connected')

    # NOTE: Do not set this field directly. Use ``set_auth()``
    user_settings = fields.AbstractForeignField()

    # The existence of this property is used to determine whether or not
    #   an addon instance is an "OAuth addon" in
    #   AddonModelMixin.get_oauth_addons().
    oauth_provider = None

    @property
    def folder_id(self):
        raise NotImplementedError(
            "AddonOAuthNodeSettingsBase subclasses must expose a 'folder_id' property."
        )

    @property
    def folder_name(self):
        raise NotImplementedError(
            "AddonOAuthNodeSettingsBase subclasses must expose a 'folder_name' property."
        )

    @property
    def folder_path(self):
        raise NotImplementedError(
            "AddonOAuthNodeSettingsBase subclasses must expose a 'folder_path' property."
        )

    @property
    def nodelogger(self):
        auth = None
        if self.user_settings:
            auth = Auth(self.user_settings.owner)
        self._logger_class = getattr(
            self,
            '_logger_class',
            type(
                '{0}NodeLogger'.format(self.config.short_name.capitalize()),
                (logger.AddonNodeLogger, ),
                {'addon_short_name': self.config.short_name}
            )
        )
        return self._logger_class(
            node=self.owner,
            auth=auth
        )

    @property
    def complete(self):
        return bool(
            self.has_auth and
            self.external_account and
            self.user_settings.verify_oauth_access(
                node=self.owner,
                external_account=self.external_account,
            )
        )

    @property
    def has_auth(self):
        """Instance has an external account and *active* permission to use it"""
        return bool(
            self.user_settings and self.user_settings.has_auth
        ) and bool(
            self.external_account and self.user_settings.verify_oauth_access(
                node=self.owner,
                external_account=self.external_account
            )
        )

    def clear_settings(self):
        raise NotImplementedError(
            "AddonOAuthNodeSettingsBase subclasses must expose a 'clear_settings' method."
        )

    def set_auth(self, external_account, user, metadata=None, log=True):
        """Connect the node addon to a user's external account.

        This method also adds the permission to use the account in the user's
        addon settings.
        """
        # tell the user's addon settings that this node is connected to it
        user_settings = user.get_or_add_addon(self.oauth_provider.short_name)
        user_settings.grant_oauth_access(
            node=self.owner,
            external_account=external_account,
            metadata=metadata  # metadata can be passed in when forking
        )
        user_settings.save()

        # update this instance
        self.user_settings = user_settings
        self.external_account = external_account

        if log:
            self.nodelogger.log(action="node_authorized", save=True)
        self.save()

    def deauthorize(self, auth=None, add_log=False):
        """Remove authorization from this node.

        This method should be overridden for addon-specific behavior,
        such as logging and clearing non-generalizable settings.
        """
        self.clear_auth()

    def clear_auth(self):
        """Disconnect the node settings from the user settings.

        This method does not remove the node's permission in the user's addon
        settings.
        """
        self.external_account = None
        self.user_settings = None
        self.save()

    def before_remove_contributor_message(self, node, removed):
        """If contributor to be removed authorized this addon, warn that removing
        will remove addon authorization.
        """
        if self.has_auth and self.user_settings.owner == removed:
            return (
                u'The {addon} add-on for this {category} is authenticated by {name}. '
                u'Removing this user will also remove write access to {addon} '
                u'unless another contributor re-authenticates the add-on.'
            ).format(
                addon=self.config.full_name,
                category=node.project_or_component,
                name=removed.fullname,
            )

    # backwards compatibility
    before_remove_contributor = before_remove_contributor_message

    def after_remove_contributor(self, node, removed, auth=None):
        """If removed contributor authorized this addon, remove addon authorization
        from owner.
        """
        if self.user_settings and self.user_settings.owner == removed:

            # Delete OAuth tokens
            self.user_settings.oauth_grants[self.owner._id].pop(self.external_account._id)
            self.clear_auth()
            message = (
                u'Because the {addon} add-on for {category} "{title}" was authenticated '
                u'by {user}, authentication information has been deleted.'
            ).format(
                addon=self.config.full_name,
                category=node.category_display,
                title=node.title,
                user=removed.fullname
            )

            if not auth or auth.user != removed:
                url = node.web_url_for('node_setting')
                message += (
                    u' You can re-authenticate on the <u><a href="{url}">Settings</a></u> page.'
                ).format(url=url)
            #
            return message

    def after_fork(self, node, fork, user, save=True):
        """After forking, copy user settings if the user is the one who authorized
        the addon.

        :return: A tuple of the form (cloned_settings, message)
        """
        clone, _ = super(AddonOAuthNodeSettingsBase, self).after_fork(
            node=node,
            fork=fork,
            user=user,
            save=False,
        )
        if self.has_auth and self.user_settings.owner == user:
            metadata = None
            if self.complete:
                try:
                    metadata = self.user_settings.oauth_grants[node._id][self.external_account._id]
                except (KeyError, AttributeError):
                    pass
            clone.set_auth(self.external_account, user, metadata=metadata, log=False)
            message = '{addon} authorization copied to forked {category}.'.format(
                addon=self.config.full_name,
                category=fork.project_or_component,
            )
        else:
            message = (
                u'{addon} authorization not copied to forked {category}. You may '
                u'authorize this fork on the <u><a href="{url}">Settings</a></u> '
                u'page.'
            ).format(
                addon=self.config.full_name,
                url=fork.web_url_for('node_setting'),
                category=fork.project_or_component,
            )
        if save:
            clone.save()
        return clone, message

    def before_register_message(self, node, user):
        """Return warning text to display if user auth will be copied to a
        registration.
        """
        if self.has_auth:
            return (
                u'The contents of {addon} add-ons cannot be registered at this time; '
                u'the {addon} add-on linked to this {category} will not be included '
                u'as part of this registration.'
            ).format(
                addon=self.config.full_name,
                category=node.project_or_component,
            )

    # backwards compatibility
    before_register = before_register_message

    def serialize_waterbutler_credentials(self):
        raise NotImplementedError(
            "AddonOAuthNodeSettingsBase subclasses must implement a 'serialize_waterbutler_credentials' method."
        )

    def serialize_waterbutler_settings(self):
        raise NotImplementedError(
            "AddonOAuthNodeSettingsBase subclasses must implement a 'serialize_waterbutler_settings' method."
        )


# TODO: No more magicks
def init_addon(app, addon_name, routes=True):
    """Load addon module return its create configuration object.

    If `log_fp` is provided, the addon's log templates will be appended
    to the file.

    :param app: Flask app object
    :param addon_name: Name of addon directory
    :param file log_fp: File pointer for the built logs file.
    :param bool routes: Add routes
    :return AddonConfig: AddonConfig configuration object if module found,
        else None

    """
    import_path = 'website.addons.{0}'.format(addon_name)

    # Import addon module
    addon_module = importlib.import_module(import_path)

    data = vars(addon_module)

    # Add routes
    if routes:
        for route_group in getattr(addon_module, 'ROUTES', []):
            process_rules(app, **route_group)

    # Build AddonConfig object
    return AddonConfig(
        **{
            key.lower(): value
            for key, value in data.iteritems()
        }
    )
