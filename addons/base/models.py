import abc
import os
import time

import markupsafe
import requests
from django.db import models
from framework.auth import Auth
from framework.auth.decorators import must_be_logged_in
from framework.exceptions import HTTPError, PermissionsError
from mako.lookup import TemplateLookup
from osf.models.base import BaseModel, ObjectIDMixin
from osf.models.external import ExternalAccount
from osf.models.node import AbstractNode
from osf.models.user import OSFUser
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from website import settings
from addons.base import logger, serializer
from website.oauth.signals import oauth_complete

lookup = TemplateLookup(
    directories=[
        settings.TEMPLATES_PATH
    ],
    default_filters=[
        'unicode',  # default filter; must set explicitly when overriding
        # FIXME: Temporary workaround for data stored in wrong format in DB. Unescape it before it
        # gets re-escaped by Markupsafe. See [#OSF-4432]
        'temp_ampersand_fixer',
        'h',
    ],
    imports=[
        # FIXME: Temporary workaround for data stored in wrong format in DB. Unescape it before it
        # gets re-escaped by Markupsafe. See [#OSF-4432]
        'from website.util.sanitize import temp_ampersand_fixer',
    ]
)


class BaseAddonSettings(ObjectIDMixin, BaseModel):
    deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True

    @property
    def config(self):
        return self._meta.app_config

    @property
    def short_name(self):
        return self.config.short_name

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


class BaseUserSettings(BaseAddonSettings):
    owner = models.OneToOneField(OSFUser, related_name='%(app_label)s_user_settings',
                                 blank=True, null=True, on_delete=models.CASCADE)

    class Meta:
        abstract = True

    @property
    def public_id(self):
        return None

    @property
    def has_auth(self):
        """Whether the user has added credentials for this addon."""
        return False

    # TODO: Test me @asmacdo
    @property
    def nodes_authorized(self):
        """Get authorized, non-deleted nodes. Returns an empty list if the
        attached add-on does not include a node model.
        """
        model = self.config.node_settings
        if not model:
            return []
        return [obj.owner for obj in model.objects.filter(user_settings=self, owner__is_deleted=False).select_related('owner')]

    @property
    def can_be_merged(self):
        return hasattr(self, 'merge')

    def to_json(self, user):
        ret = super(BaseUserSettings, self).to_json(user)
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

    def __repr__(self):
        if self.owner:
            return '<{cls} owned by user {uid}>'.format(cls=self.__class__.__name__, uid=self.owner._id)
        return '<{cls} with no owner>'.format(cls=self.__class__.__name__)


@oauth_complete.connect
def oauth_complete(provider, account, user):
    if not user or not account:
        return
    user.add_addon(account.provider)
    user.save()


class BaseOAuthUserSettings(BaseUserSettings):
    # Keeps track of what nodes have been given permission to use external
    #   accounts belonging to the user.
    oauth_grants = DateTimeAwareJSONField(default=dict, blank=True)
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

    class Meta:
        abstract = True

    @property
    def has_auth(self):
        return self.external_accounts.exists()

    @property
    def external_accounts(self):
        """The user's list of ``ExternalAccount`` instances for this provider"""
        return self.owner.external_accounts.filter(provider=self.oauth_provider.short_name)

    def delete(self, save=True):
        for account in self.external_accounts.filter(provider=self.config.short_name):
            self.revoke_oauth_access(account, save=False)
        super(BaseOAuthUserSettings, self).delete(save=save)

    def grant_oauth_access(self, node, external_account, metadata=None):
        """Give a node permission to use an ``ExternalAccount`` instance."""
        # ensure the user owns the external_account
        if not self.owner.external_accounts.filter(id=external_account.id).exists():
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
                node.get_addon(external_account.provider, deleted=True).deauthorize(auth=auth)
            except AttributeError:
                # No associated addon settings despite oauth grant
                pass

        if external_account.osfuser_set.count() == 1 and \
                external_account.osfuser_set.filter(id=auth.user.id).exists():
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
            node = AbstractNode.load(node_id)
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
            Model = config.models['nodesettings']
        except KeyError:
            pass
        else:
            Model.objects.filter(user_settings=user_settings).update(user_settings=self)

        self.save()

    def to_json(self, user):
        ret = super(BaseOAuthUserSettings, self).to_json(user)

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
        super(BaseOAuthUserSettings, self).on_delete()
        nodes = [AbstractNode.load(node_id) for node_id in self.oauth_grants.keys()]
        for node in nodes:
            node_addon = node.get_addon(self.oauth_provider.short_name)
            if node_addon and node_addon.user_settings == self:
                node_addon.clear_auth()


class BaseNodeSettings(BaseAddonSettings):
    owner = models.OneToOneField(AbstractNode, related_name='%(app_label)s_node_settings',
                                 null=True, blank=True, on_delete=models.CASCADE)

    class Meta:
        abstract = True

    @property
    def complete(self):
        """Whether or not this addon is properly configured
        :rtype bool:
        """
        raise NotImplementedError()

    @property
    def configured(self):
        """Whether or not this addon has had a folder connected.
        :rtype bool:
        """
        return self.complete

    @property
    def has_auth(self):
        """Whether the node has added credentials for this addon."""
        return False

    def to_json(self, user):
        ret = super(BaseNodeSettings, self).to_json(user)
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

        if hasattr(self, 'user_settings'):
            if self.user_settings is None:
                return (
                    u'Because you have not configured the {addon} add-on, your authentication will not be '
                    u'transferred to the forked {category}. You may authorize and configure the {addon} add-on '
                    u'in the new fork on the settings page.'
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
                    u'{category}. You may authorize and configure the {addon} add-on '
                    u'in the new fork on the settings page.'
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
        :returns: cloned settings

        """
        clone = self.clone()
        clone.user_settings = None
        clone.owner = fork

        if save:
            clone.save()

        return clone

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

    def after_delete(self, user):
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


class BaseStorageAddon(object):
    """
    Mixin class for traversing file trees of addons with files
    """

    root_node = GenericRootNode()

    class Meta:
        abstract = True

    @property
    def archive_folder_name(self):
        name = 'Archive of {addon}'.format(addon=self.config.full_name)
        folder_name = getattr(self, 'folder_name', '').lstrip('/').strip()
        if folder_name:
            name = name + ': {folder}'.format(folder=folder_name)
        return name

    def _get_fileobj_child_metadata(self, filenode, user, cookie=None, version=None):
        from api.base.utils import waterbutler_api_url_for

        kwargs = {}
        if version:
            kwargs['version'] = version
        if cookie:
            kwargs['cookie'] = cookie
        elif user:
            kwargs['cookie'] = user.get_or_create_cookie()

        metadata_url = waterbutler_api_url_for(
            self.owner.osfstorage_region.waterbutler_url,
            self.owner._id,
            self.config.short_name,
            path=filenode.get('path', '/'),
            user=user,
            view_only=True,
            _internal=True,
            **kwargs
        )

        res = requests.get(metadata_url)

        if res.status_code != 200:
            raise HTTPError(res.status_code, data={'error': res.json()})

        # TODO: better throttling?
        time.sleep(1.0 / 5.0)

        data = res.json().get('data', None)
        if data:
            return [child['attributes'] for child in data]
        return []

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

        kwargs = {
            'version': version,
            'cookie': cookie,
        }
        filenode['children'] = [
            self._get_file_tree(child, user, cookie=cookie)
            for child in self._get_fileobj_child_metadata(filenode, user, **kwargs)
        ]
        return filenode


class BaseOAuthNodeSettings(BaseNodeSettings):
    # TODO: Validate this field to be sure it matches the provider's short_name
    # NOTE: Do not set this field directly. Use ``set_auth()``
    external_account = models.ForeignKey(ExternalAccount, null=True, blank=True,
                                         related_name='%(app_label)s_node_settings',
                                         on_delete=models.CASCADE)

    # NOTE: Do not set this field directly. Use ``set_auth()``
    # user_settings = fields.AbstractForeignField()

    # The existence of this property is used to determine whether or not
    #   an addon instance is an "OAuth addon" in
    #   AddonModelMixin.get_oauth_addons().
    oauth_provider = None

    class Meta:
        abstract = True

    @abc.abstractproperty
    def folder_id(self):
        raise NotImplementedError(
            "BaseOAuthNodeSettings subclasses must expose a 'folder_id' property."
        )

    @abc.abstractproperty
    def folder_name(self):
        raise NotImplementedError(
            "BaseOAuthNodeSettings subclasses must expose a 'folder_name' property."
        )

    @abc.abstractproperty
    def folder_path(self):
        raise NotImplementedError(
            "BaseOAuthNodeSettings subclasses must expose a 'folder_path' property."
        )

    def fetch_folder_name(self):
        return self.folder_name

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
                (logger.AddonNodeLogger,),
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
    def configured(self):
        return bool(
            self.complete and
            (self.folder_id or self.folder_name or self.folder_path)
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
            "BaseOAuthNodeSettings subclasses must expose a 'clear_settings' method."
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
            self.nodelogger.log(action='node_authorized', save=True)
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
            self.user_settings.save()
            self.clear_auth()
            message = (
                u'Because the {addon} add-on for {category} "{title}" was authenticated '
                u'by {user}, authentication information has been deleted.'
            ).format(
                addon=self.config.full_name,
                category=markupsafe.escape(node.category_display),
                title=markupsafe.escape(node.title),
                user=markupsafe.escape(removed.fullname)
            )

            if not auth or auth.user != removed:
                url = node.web_url_for('node_addons')
                message += (
                    u' You can re-authenticate on the <u><a href="{url}">add-ons</a></u> page.'
                ).format(url=url)
            #
            return message

    def after_fork(self, node, fork, user, save=True):
        """After forking, copy user settings if the user is the one who authorized
        the addon.

        :return: the cloned settings
        """
        clone = super(BaseOAuthNodeSettings, self).after_fork(
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
        else:
            clone.clear_settings()
        if save:
            clone.save()
        return clone

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
        raise NotImplementedError("BaseOAuthNodeSettings subclasses must implement a \
            'serialize_waterbutler_credentials' method.")

    def serialize_waterbutler_settings(self):
        raise NotImplementedError("BaseOAuthNodeSettings subclasses must implement a \
            'serialize_waterbutler_settings' method.")


class BaseCitationsNodeSettings(BaseOAuthNodeSettings):
    class Meta:
        abstract = True

    def serialize_waterbutler_settings(self, *args, **kwargs):
        # required by superclass, not actually used
        pass

    def serialize_waterbutler_credentials(self, *args, **kwargs):
        # required by superclass, not actually used
        pass

    def create_waterbutler_log(self, *args, **kwargs):
        # required by superclass, not actually used
        pass

    @property
    def api(self):
        """authenticated ExternalProvider instance"""
        if self._api is None:
            self._api = self.oauth_provider(account=self.external_account)
        return self._api

    @property
    def complete(self):
        """Boolean indication of addon completeness"""
        return bool(self.has_auth and self.user_settings.verify_oauth_access(
            node=self.owner,
            external_account=self.external_account,
            metadata={'folder': self.list_id},
        ))

    @property
    def root_folder(self):
        """Serialized representation of root folder"""
        return self.serializer.serialized_root_folder

    @property
    def folder_id(self):
        return self.list_id

    @property
    def folder_name(self):
        return self.fetch_folder_name

    @property
    def folder_path(self):
        return self.fetch_folder_name

    @property
    def fetch_folder_name(self):
        """Returns a displayable folder name"""
        if self.list_id is None:
            return ''
        elif self.list_id == 'ROOT':
            return 'All Documents'
        else:
            return self._fetch_folder_name

    def clear_settings(self):
        """Clears selected folder configuration"""
        self.list_id = None

    def set_auth(self, *args, **kwargs):
        """Connect the node addon to a user's external account.

        This method also adds the permission to use the account in the user's
        addon settings.
        """
        self.list_id = None
        self.save()

        return super(BaseCitationsNodeSettings, self).set_auth(*args, **kwargs)

    def deauthorize(self, auth=None, add_log=True):
        """Remove user authorization from this node and log the event."""
        if add_log:
            self.owner.add_log(
                '{0}_node_deauthorized'.format(self.provider_name),
                params={
                    'project': self.owner.parent_id,
                    'node': self.owner._id,
                },
                auth=auth,
            )

        self.clear_settings()
        self.clear_auth()
        self.save()

    def after_delete(self, user=None):
        self.deauthorize(Auth(user=user), add_log=True)

    def on_delete(self):
        self.deauthorize(add_log=False)
