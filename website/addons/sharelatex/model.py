# -*- coding: utf-8 -*-

from modularodm import fields

from framework.auth.core import Auth

from website.addons.base import exceptions
from website.addons.base import AddonUserSettingsBase, AddonNodeSettingsBase
from website.addons.base import StorageAddonBase

from website.addons.sharelatex import utils


class AddonShareLatexUserSettings(AddonUserSettingsBase):

    sharelatex_url = fields.StringField()
    auth_token = fields.StringField()

    def to_json(self, user):
        ret = super(AddonShareLatexUserSettings, self).to_json(user)
        ret['has_auth'] = self.has_auth
        if self.owner:
            ret['name'] = self.owner.display_full_name()
            ret['profile_url'] = self.owner.profile_url
        return ret

    @property
    def has_auth(self):
        return bool(self.sharelatex_url and self.auth_token)

    @property
    def is_valid(self):
        return utils.can_list(self.sharelatex_url, self.auth_token)

    def revoke_auth(self, auth=None, save=False):
        for node_settings in self.addonsharelatexnodesettings__authorized:
            node_settings.deauthorize(auth=auth, save=True)

        self.sharelatex_osf_user, self.sharelatex_url, self.auth_token = None, None, None

        if save:
            self.save()

        return True


class AddonShareLatexNodeSettings(StorageAddonBase, AddonNodeSettingsBase):

    project = fields.StringField()
    user_settings = fields.ForeignField(
        'addonsharelatexusersettings', backref='authorized'
    )

    @property
    def folder_name(self):
        return self.project

    @property
    def display_name(self):
        return u'{0}: {1}'.format(self.config.full_name, self.project)

    @property
    def complete(self):
        return self.has_auth and self.project is not None

    def authorize(self, user_settings, save=False):
        self.user_settings = user_settings
        self.owner.add_log(
            action='sharelatex_node_authorized',
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
            },
            auth=Auth(user_settings.owner),
        )
        if save:
            self.save()

    def deauthorize(self, auth=None, log=True, save=False):
        self.project, self.user_settings = None, None

        if log:
            self.owner.add_log(
                action='sharelatex_node_deauthorized',
                params={
                    'project': self.owner.parent_id,
                    'node': self.owner._id,
                },
                auth=auth,
            )
        if save:
            self.save()

    def delete(self, save=True):
        self.deauthorize(log=False, save=False)
        super(AddonShareLatexNodeSettings, self).delete(save=save)

    def serialize_waterbutler_credentials(self):
        if not self.has_auth:
            raise exceptions.AddonError('Cannot serialize credentials for ShareLatex addon')
        return {
            'sharelatex_url': self.user_settings.sharelatex_url,
            'auth_token': self.user_settings.auth_token,
        }

    def serialize_waterbutler_settings(self):
        if not self.project:
            raise exceptions.AddonError('Cannot serialize settings for ShareLatex addon')
        return {
            'project': self.project,
        }

    def create_waterbutler_log(self, auth, action, metadata):
        url = self.owner.web_url_for('addon_view_or_download_file', provider='sharelatex', path=metadata['path'])

        self.owner.add_log(
            'sharelatex_{0}'.format(action),
            auth=auth,
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'path': metadata['materialized'],
                'project': self.project,
                'urls': {
                    'view': url,
                    'download': url + '?action=download'
                }
            },
        )

    def to_json(self, user):
        ret = super(AddonShareLatexNodeSettings, self).to_json(user)

        user_settings = user.get_addon('sharelatex')

        ret.update({
            'project': self.project or '',
            'has_project': self.project is not None,
            'user_is_owner': (
                self.user_settings and self.user_settings.owner == user
            ),
            'user_has_auth': bool(user_settings) and user_settings.has_auth,
            'node_has_auth': self.has_auth,
            'owner': None,
            'project_list': None,
            'valid_credentials': user_settings and user_settings.is_valid,
        })

        if self.has_auth:
            ret['owner'] = self.user_settings.owner.fullname
            ret['owner_url'] = self.user_settings.owner.url
            ret['node_has_auth'] = True

        return ret

    @property
    def has_auth(self):
        return bool(self.user_settings and self.user_settings.has_auth)
        #TODO Update callbacks

    def before_register(self, node, user):
        """

        :param Node node:
        :param User user:
        :return str: Alert message

        """
        category = node.project_or_component
        if self.user_settings and self.user_settings.has_auth:
            return (
                u'The contents of ShareLatex add-ons cannot be registered at this time; '
                u'the ShareLatex project linked to this {category} will not be included '
                u'as part of this registration.'
            ).format(**locals())

    def after_fork(self, node, fork, user, save=True):
        """

        :param Node node: Original node
        :param Node fork: Forked node
        :param User user: User creating fork
        :param bool save: Save settings after callback
        :return tuple: Tuple of cloned settings and alert message

        """
        clone, _ = super(AddonShareLatexNodeSettings, self).after_fork(
            node, fork, user, save=False
        )

        # Copy authentication if authenticated by forking user
        if self.user_settings and self.user_settings.owner == user:
            clone.user_settings = self.user_settings
            clone.project = self.project
            message = (
                'Amazon Simple Storage authorization copied to forked {cat}.'
            ).format(
                cat=fork.project_or_component,
            )
        else:
            message = (
                'Amazon Simple Storage authorization not copied to forked {cat}. You may '
                'authorize this fork on the <u><a href={url}>Settings</a></u> '
                'page.'
            ).format(
                cat=fork.project_or_component,
                url=fork.url + 'settings/'
            )

        if save:
            clone.save()

        return clone, message

    def before_remove_contributor(self, node, removed):
        """

        :param Node node:
        :param User removed:
        :return str: Alert message

        """
        if self.user_settings and self.user_settings.owner == removed:
            return (
                'The Amazon Simple Storage add-on for this {category} is authenticated '
                'by {user}. Removing this user will also remove access '
                'to {project} unless another contributor re-authenticates.'
            ).format(
                category=node.project_or_component,
                user=removed.fullname,
                project=self.project
            )

    def after_remove_contributor(self, node, removed, auth=None):
        """

        :param Node node:
        :param User removed:
        :return str: Alert message

        """
        if self.user_settings and self.user_settings.owner == removed:
            self.user_settings = None
            self.project = None
            self.save()

            message = (
                u'Because the Amazon Simple Storage add-on for {category} "{title}" was '
                u'authenticated by {user}, authentication information has been deleted.'
            ).format(category=node.category_display, title=node.title, user=removed.fullname)

            if not auth or auth.user != removed:
                url = node.web_url_for('node_setting')
                message += (
                    u' You can re-authenticate on the <u><a href="{url}">Settings</a></u> page.'
                ).format(url=url)
            #
            return message

    def after_delete(self, node, user):
        self.deauthorize(Auth(user=user), log=True, save=True)
