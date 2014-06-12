import os
from framework import fields
from website.addons.base import AddonNodeSettingsBase, AddonUserSettingsBase
from website.addons.base import GuidFile

from .api import Figshare
from . import settings as figshare_settings
from . import messages


class FigShareGuidFile(GuidFile):

    article_id = fields.StringField(index=True)
    file_id = fields.StringField(index=True)

    @property
    def file_url(self):
        if self.article_id is None or self.file_id is None:
            raise ValueError('Path field must be defined.')
        return os.path.join('figshare', 'article', self.article_id, 'file', self.file_id)


class AddonFigShareUserSettings(AddonUserSettingsBase):

    oauth_request_token = fields.StringField()
    oauth_request_token_secret = fields.StringField()
    oauth_access_token = fields.StringField()
    oauth_access_token_secret = fields.StringField()

    @property
    def has_auth(self):
        return self.oauth_access_token is not None

    def remove_auth(self):
        self.oauth_access_token = None
        self.oauth_access_token_secret = None

    def to_json(self, user):
        rv = super(AddonFigShareUserSettings, self).to_json(user)
        rv.update({
            'authorized': self.has_auth,
        })
        return rv


class AddonFigShareNodeSettings(AddonNodeSettingsBase):

    figshare_id = fields.StringField()
    figshare_type = fields.StringField()
    figshare_title = fields.StringField()

    user_settings = fields.ForeignField(
        'addonfigshareusersettings', backref='authorized'
    )

    @property
    def embed_url(self):
        return 'http://wl.figshare.com/articles/{fid}/embed?show_title=1'.format(
            fid=self.figshare_id,
        )

    @property
    def api_url(self):
        if self.user_settings is None:
            return figshare_settings.API_URL
        else:
            return figshare_settings.API_OAUTH_URL

    @property
    def has_auth(self):
        return bool(self.user_settings and self.user_settings.has_auth)

    @property
    def linked_content(self):
        return {'id': self.figshare_id, 'type': self.figshare_type, 'title': self.figshare_title}

    def update_fields(self, fields, node, auth):        
        updated = False
        if fields.get('id'):
            updated = updated or (fields['id'] != self.figshare_id)
            self.figshare_id = fields['id']
        if fields.get('title'):
            updated = updated or (fields['title'] != self.figshare_title)
            self.figshare_title = fields['title']            
        if fields.get('type'):
            updated = updated or (fields['type'] != self.figshare_type)
            self.figshare_type = fields['type']            

        self.save()
        if updated:
            node.add_log(
                action='figshare_content_linked',
                params={
                    'project': node.parent_id,
                    'node': node._id,
                    'figshare': {
                        'type': self.figshare_type,
                        'id': self.figshare_id,
                        'title': self.figshare_title,
                        }
                    },
                auth=auth,
                )

    def to_json(self, user):
        rv = super(AddonFigShareNodeSettings, self).to_json(user)

        figshare_user = user.get_addon('figshare')

        rv.update({
            'figshare_id': self.figshare_id or '',
            'figshare_type': self.figshare_type or '',
            'figshare_title': self.figshare_title or '',
            'node_has_auth': self.has_auth,
            'user_has_auth': figshare_user and figshare_user.has_auth,
            'figshare_options': [],
            'is_registration': self.owner.is_registration,
        })
        if self.has_auth:
            rv.update({
                'authorized_user': self.user_settings.owner.fullname,
                'owner_url': self.user_settings.owner.url,
                'is_owner': user == self.user_settings.owner
            })

        return rv

    #############
    # Callbacks #
    #############

    def before_page_load(self, node, user):
        """

        :param Node node:
        :param User user:
        :return str: Alert message

        """
        if not self.figshare_id:
            return []
        figshare = node.get_addon('figshare')
        # Quit if no user authorization

        node_permissions = 'public' if node.is_public else 'private'

        if figshare.figshare_type == 'project':
            if node_permissions == 'private':
                message = messages.BEFORE_PAGE_LOAD_PRIVATE_NODE_MIXED_FS.format(category=node.project_or_component, project_id=figshare.figshare_id)
                return [message]
            else:
                message = messages.BEFORE_PAGE_LOAD_PUBLIC_NODE_MIXED_FS.format(category=node.project_or_component, project_id=figshare.figshare_id)

        connect = Figshare.from_settings(self.user_settings)
        article_is_public = connect.article_is_public(self.figshare_id)

        article_permissions = 'public' if article_is_public else 'private'

        if article_permissions != node_permissions:
            message = messages.BEFORE_PAGE_LOAD_PERM_MISMATCH.format(
                    category=node.project_or_component,
                    node_perm=node_permissions,
                    figshare_perm=article_permissions,
                    figshare_id=self.figshare_id,
                )
            if article_permissions == 'private' and node_permissions == 'public':
                message += messages.BEFORE_PAGE_LOAD_PUBLIC_NODE_PRIVATE_FS
            return [message]

    def before_remove_contributor(self, node, removed):
        """

        :param Node node:
        :param User removed:
        :return str: Alert message

        """
        if self.user_settings and self.user_settings.owner == removed:
            return messages.BEFORE_REMOVE_CONTRIBUTOR.format(
                category=node.project_or_component,
                user=removed.fullname,
                )

    def after_remove_contributor(self, node, removed):
        """

        :param Node node:
        :param User removed:
        :return str: Alert message

        """
        if self.user_settings and self.user_settings.owner == removed:

            # Delete OAuth tokens
            self.user_settings = None
            self.save()

            return messages.AFTER_REMOVE_CONTRIBUTOR.format(
                    user=removed.fullname,
                    url=node.url,
                    category=self.figshare_id
                    )

    def before_fork(self, node, user):
        """

        :param Node node:
        :param User user:
        :return str: Alert message

        """
        if self.user_settings and self.user_settings.owner == user:
            return messages.BEFORE_FORK_OWNER.format(
                category=node.project_or_component,
                )
        return messages.BEFORE_FORK_NOT_OWNER.format(
            category=node.project_or_component,
            )

    def after_fork(self, node, fork, user, save=True):
        """

        :param Node node: Original node
        :param Node fork: Forked node
        :param User user: User creating fork
        :param bool save: Save settings after callback
        :return tuple: Tuple of cloned settings and alert message

        """
        clone, _ = super(AddonFigShareNodeSettings, self).after_fork(
            node, fork, user, save=False
            )

        # Copy authentication if authenticated by forking user
        if self.user_settings and self.user_settings.owner == user:
            clone.user_settings = self.user_settings
            message = messages.AFTER_FORK_OWNER.format(
                category=fork.project_or_component,
                )
        else:
            message = messages.AFTER_FORK_NOT_OWNER.format(
                category=fork.project_or_component,
                url=fork.url + 'settings/'
                )
            return AddonFigShareNodeSettings(), message

        if save:
            clone.save()

        return clone, message
